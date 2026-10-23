from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.paths import UnsafeServerPath, resolve_inside, resolve_server_root


def test_defaults_bind_only_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(__import__("os").environ):
        if key.startswith("MCDASH_"):
            monkeypatch.delenv(key, raising=False)
    settings = Settings.from_env()
    assert settings.bind_host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.server_dir is None
    assert settings.server_host == "127.0.0.1"
    assert settings.server_port == 25565
    assert settings.server_type == "unknown"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("MCDASH_BIND_HOST", "0.0.0.0"),
        ("MCDASH_PORT", "70000"),
        ("MCDASH_SERVER_PORT", "nope"),
        ("MCDASH_SERVER_TYPE", "custom-launcher"),
        ("MCDASH_LOG_PATH", "../outside.log"),
        ("MCDASH_LOG_PATH", "/etc/passwd"),
        ("MCDASH_STATUS_TIMEOUT", "30"),
    ],
)
def test_invalid_configuration_is_rejected(monkeypatch: pytest.MonkeyPatch, key: str, value: str) -> None:
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_resolve_inside_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(UnsafeServerPath):
        resolve_inside(tmp_path, "../outside")


def test_resolve_inside_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "server"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (root / "logs").symlink_to(outside)

    with pytest.raises(UnsafeServerPath):
        resolve_inside(root.resolve(), "logs")


def test_missing_configured_root_is_unavailable(tmp_path: Path) -> None:
    assert resolve_server_root(tmp_path / "does-not-exist") is None
