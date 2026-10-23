from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app import monitoring
from app.monitoring import (
    MAX_STATUS_PACKET,
    _read_varint,
    _varint,
    _description_text,
    host_metrics,
    mods_inventory,
    player_status,
    query_java_status,
    server_logs,
    server_status,
)


def test_varint_round_trip_values() -> None:
    for value, encoded in [(0, b"\x00"), (127, b"\x7f"), (128, b"\x80\x01"), (767, b"\xff\x05")]:
        assert _read_varint(encoded) == (value, len(encoded))


def test_missing_server_dir_is_explicitly_unavailable() -> None:
    settings = Settings(server_dir=None)
    assert server_logs(settings)["state"] == "unavailable"
    assert mods_inventory(settings)["state"] == "unavailable"


def test_missing_mods_directory_is_an_available_empty_inventory(tmp_path: Path) -> None:
    assert mods_inventory(Settings(server_dir=tmp_path)) == {
        "state": "available",
        "items": [],
        "reason": None,
    }


def test_logs_are_bounded_and_control_characters_removed(tmp_path: Path) -> None:
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "latest.log").write_text("first\nsecond\x1b[31m red\n", encoding="utf-8")
    settings = Settings(server_dir=tmp_path, max_log_lines=1)

    result = server_logs(settings)
    assert result["state"] == "available"
    assert len(result["lines"]) == 1
    assert result["lines"][0] == "second[31m red"


def test_logs_reject_symlink_to_outside_file(tmp_path: Path) -> None:
    root = tmp_path / "server"
    (root / "logs").mkdir(parents=True)
    outside = tmp_path / "outside.log"
    outside.write_text("private", encoding="utf-8")
    (root / "logs" / "latest.log").symlink_to(outside)

    result = server_logs(Settings(server_dir=root))
    assert result["state"] == "unavailable"
    assert result["lines"] == []


def test_logs_reject_symlink_swap_after_containment_validation(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "server"
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "latest.log").write_text("safe", encoding="utf-8")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "latest.log").write_text("must not be read", encoding="utf-8")
    original_resolve = monitoring.resolve_inside

    def validate_then_swap(base: Path, relative: str | Path, *, must_exist: bool = True) -> Path:
        resolved = original_resolve(base, relative, must_exist=must_exist)
        if str(relative) == "logs/latest.log":
            (root / "logs").rename(root / "logs-before-swap")
            (root / "logs").symlink_to(outside_dir, target_is_directory=True)
        return resolved

    monkeypatch.setattr(monitoring, "resolve_inside", validate_then_swap)
    result = server_logs(Settings(server_dir=root))
    assert result["state"] == "unavailable"
    assert result["lines"] == []


def test_mods_reject_symlink_swap_after_containment_validation(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "server"
    mods_dir = root / "mods"
    mods_dir.mkdir(parents=True)
    (mods_dir / "safe.jar").write_bytes(b"safe")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "private.jar").write_bytes(b"private")
    original_resolve = monitoring.resolve_inside

    def validate_then_swap(base: Path, relative: str | Path, *, must_exist: bool = True) -> Path:
        resolved = original_resolve(base, relative, must_exist=must_exist)
        if str(relative) == "mods":
            (root / "mods").rename(root / "mods-before-swap")
            (root / "mods").symlink_to(outside_dir, target_is_directory=True)
        return resolved

    monkeypatch.setattr(monitoring, "resolve_inside", validate_then_swap)
    result = mods_inventory(Settings(server_dir=root))
    assert result["state"] == "unavailable"
    assert result["items"] == []


def test_oversized_status_packet_returns_unknown_tuple(monkeypatch) -> None:
    fake_socket = _FakeStatusSocket(b"", declared_length=MAX_STATUS_PACKET + 1)
    monkeypatch.setattr(monitoring.socket, "create_connection", lambda *_a, **_kw: fake_socket)

    assert query_java_status(Settings()) == (None, "unknown")


@pytest.mark.parametrize(
    "response",
    [
        b"\x01",  # Unexpected packet ID.
        b"\x00\x05{}",  # JSON length exceeds the payload length.
    ],
)
def test_malformed_status_responses_return_unknown_tuple(monkeypatch, response: bytes) -> None:
    fake_socket = _FakeStatusSocket(response)
    monkeypatch.setattr(monitoring.socket, "create_connection", lambda *_a, **_kw: fake_socket)

    assert query_java_status(Settings()) == (None, "unknown")


def test_deeply_nested_status_json_returns_unknown(monkeypatch) -> None:
    document = b'{"description":' + b"[" * 1200 + b"0" + b"]" * 1200 + b"}"
    response = b"\x00" + _varint(len(document)) + document
    fake_socket = _FakeStatusSocket(response)
    monkeypatch.setattr(monitoring.socket, "create_connection", lambda *_a, **_kw: fake_socket)

    assert query_java_status(Settings()) == (None, "unknown")


def test_deep_description_components_are_bounded_without_recursion() -> None:
    description: dict = {"text": "deep"}
    for _ in range(1500):
        description = {"extra": [description]}

    assert _description_text(description) is None


class _FakeStatusSocket:
    def __init__(self, packet: bytes, *, declared_length: int | None = None) -> None:
        length = len(packet) if declared_length is None else declared_length
        self.received = bytearray(_varint(length) + packet)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def settimeout(self, _timeout: float) -> None:
        pass

    def sendall(self, _data: bytes) -> None:
        pass

    def recv(self, count: int) -> bytes:
        result = bytes(self.received[:count])
        del self.received[:count]
        return result


def test_mods_listing_skips_symlinks_and_never_reads_metadata(tmp_path: Path) -> None:
    root = tmp_path / "server"
    (root / "mods").mkdir(parents=True)
    mod = root / "mods" / "example.jar"
    mod.write_bytes(b"not a real mod archive")
    outside = tmp_path / "outside.jar"
    outside.write_bytes(b"outside")
    (root / "mods" / "external.jar").symlink_to(outside)

    result = mods_inventory(Settings(server_dir=root))
    assert result["state"] == "available"
    assert result["items"] == [{"filename": "example.jar", "size_bytes": len(b"not a real mod archive")}]


def test_host_metrics_does_not_fabricate_jvm_or_tps_values() -> None:
    result = host_metrics()
    assert result["jvm_heap_used_bytes"] is None
    assert result["jvm_heap_max_bytes"] is None
    assert result["tps"] is None
    assert result["availability"]["jvm_memory"] == "unavailable"
    assert result["availability"]["tps"] == "unavailable"


def test_refused_status_connection_reports_offline_without_invented_data(monkeypatch) -> None:
    import socket

    def refused(*args, **kwargs):
        raise ConnectionRefusedError("test")

    monkeypatch.setattr(socket, "create_connection", refused)
    settings = Settings()

    status = server_status(settings)
    players = player_status(settings)
    assert status["state"] == "offline"
    assert status["version"] is None
    assert status["uptime_seconds"] is None
    assert players == {"state": "unavailable", "online": None, "max": None, "players": [], "source": None}
