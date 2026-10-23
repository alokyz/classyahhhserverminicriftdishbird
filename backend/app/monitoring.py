"""Read-only server status, logs, mod inventory, and host metrics."""

from __future__ import annotations

import json
import socket
import struct
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .adapters import create_server_adapter
from .config import Settings
from .paths import (
    UnsafeServerPath,
    list_regular_files,
    read_bounded_tail,
    resolve_inside,
    resolve_server_root,
)

PROTOCOL_VERSION = 767  # Minecraft Java 1.21.1; status queries are usually version-agnostic.
MAX_STATUS_PACKET = 1_048_576
MAX_STATUS_JSON_DEPTH = 64


def _varint(value: int) -> bytes:
    if value < 0:
        value &= 0xFFFFFFFF
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            output.append(byte | 0x80)
        else:
            output.append(byte)
            return bytes(output)


def _read_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    result = 0
    shift = 0
    while shift < 35:
        if offset >= len(data):
            raise ValueError("incomplete status packet")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return result, offset
        shift += 7
    raise ValueError("invalid status packet integer")


def _read_exact(sock: socket.socket, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("server closed the status connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _json_depth_is_bounded(text: str, *, limit: int = MAX_STATUS_JSON_DEPTH) -> bool:
    """Reject excessively nested untrusted JSON before invoking the decoder."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > limit:
                return False
        elif char in "]}":
            depth -= 1
            if depth < 0:
                return False
    return not in_string and depth == 0


def _write_packet(sock: socket.socket, payload: bytes) -> None:
    sock.sendall(_varint(len(payload)) + payload)


def query_java_status(settings: Settings) -> tuple[dict[str, Any] | None, str]:
    """Query the standard Minecraft Java status protocol without sending commands."""
    host = settings.server_host
    host_bytes = host.encode("utf-8")
    handshake = (
        _varint(0)
        + _varint(PROTOCOL_VERSION)
        + _varint(len(host_bytes))
        + host_bytes
        + struct.pack(">H", settings.server_port)
        + _varint(1)
    )
    try:
        with socket.create_connection((host, settings.server_port), timeout=settings.status_timeout_seconds) as sock:
            sock.settimeout(settings.status_timeout_seconds)
            _write_packet(sock, handshake)
            _write_packet(sock, _varint(0))
            packet_length, _ = _receive_packet(sock)
            if packet_length > MAX_STATUS_PACKET:
                return None, "unknown"
            response = _read_exact(sock, packet_length)
        packet_id, offset = _read_varint(response)
        if packet_id != 0:
            return None, "unknown"
        json_length, offset = _read_varint(response, offset)
        if json_length < 0 or json_length > MAX_STATUS_PACKET or offset + json_length > len(response):
            return None, "unknown"
        document = response[offset : offset + json_length].decode("utf-8")
        if not _json_depth_is_bounded(document):
            return None, "unknown"
        parsed = json.loads(document)
        return (parsed, "online") if isinstance(parsed, dict) else (None, "unknown")
    except ConnectionRefusedError:
        return None, "offline"
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError, struct.error, RecursionError):
        return None, "unknown"


def _receive_packet(sock: socket.socket) -> tuple[int, bytes]:
    length = 0
    shift = 0
    while shift < 35:
        byte = _read_exact(sock, 1)[0]
        length |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return length, b""
        shift += 7
    raise ValueError("invalid packet length")


def _plain_text(value: Any, *, limit: int = 100) -> str | None:
    if not isinstance(value, str):
        return None
    return "".join(ch for ch in value if ch.isprintable())[:limit]


def _description_text(value: Any) -> str | None:
    # Minecraft descriptions can be nested JSON components. Traverse
    # iteratively with strict node/character budgets to avoid recursion errors
    # and unbounded work on server-controlled data.
    stack = [value]
    chunks: list[str] = []
    total_chars = 0
    visited = 0
    while stack and visited < 500 and total_chars < 200:
        item = stack.pop()
        visited += 1
        if isinstance(item, str):
            text = _plain_text(item, limit=200) or ""
            text = text[: 200 - total_chars]
            if text:
                chunks.append(text)
                total_chars += len(text)
        elif isinstance(item, dict):
            own = _plain_text(item.get("text"), limit=200) or ""
            own = own[: 200 - total_chars]
            if own:
                chunks.append(own)
                total_chars += len(own)
            extras = item.get("extra")
            if isinstance(extras, list):
                stack.extend(reversed(extras[:500]))
    return "".join(chunks) or None


def server_status(settings: Settings) -> dict[str, Any]:
    adapter = create_server_adapter(settings)
    status, state = adapter.status()
    version_obj = status.get("version") if status else None
    players_obj = status.get("players") if status else None
    if not isinstance(version_obj, dict):
        version_obj = {}
    if not isinstance(players_obj, dict):
        players_obj = {}
    name = settings.server_name or _description_text(status.get("description")) if status else settings.server_name
    return {
        "state": state,
        "name": name,
        "version": _plain_text(version_obj.get("name"), limit=100),
        "players_online": _nonnegative_int(players_obj.get("online")),
        "players_max": _nonnegative_int(players_obj.get("max")),
        "uptime_seconds": None,
        "sampled_at": datetime.now(UTC).isoformat(),
        "adapter": adapter.name,
        "capabilities": {
            "status_query": "available" if status is not None else "unavailable",
            "player_sample": "available" if isinstance(players_obj.get("sample"), list) else "unavailable",
            "uptime": "unavailable",
            "console_commands": "unsupported",
            "server_type": settings.server_type,
            "server_type_source": "configured" if settings.server_type != "unknown" else "unknown",
        },
    }


def player_status(settings: Settings) -> dict[str, Any]:
    status, _ = create_server_adapter(settings).status()
    if status is None:
        return {"state": "unavailable", "online": None, "max": None, "players": [], "source": None}
    payload = status.get("players")
    if not isinstance(payload, dict):
        payload = {}
    sample = payload.get("sample")
    players: list[dict[str, str | None]] = []
    if isinstance(sample, list):
        for row in sample[:100]:
            if not isinstance(row, dict):
                continue
            player_name = _plain_text(row.get("name"), limit=64)
            if not player_name:
                continue
            player_uuid = _plain_text(row.get("id"), limit=64)
            players.append({"name": player_name, "uuid": player_uuid})
    return {
        "state": "available",
        "online": _nonnegative_int(payload.get("online")),
        "max": _nonnegative_int(payload.get("max")),
        "players": players,
        "source": "minecraft-java-status",
    }


def _nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _proc_cpu_totals() -> tuple[int, int]:
    # Fixed Linux procfs metrics only; no arbitrary process data is inspected.
    with Path("/proc/stat").open("r", encoding="ascii") as handle:
        first = handle.readline().split()
    if not first or first[0] != "cpu":
        raise OSError("host CPU metrics unavailable")
    values = [int(item) for item in first[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return sum(values), idle


def _host_memory() -> tuple[int, int]:
    values: dict[str, int] = {}
    with Path("/proc/meminfo").open("r", encoding="ascii") as handle:
        for line in handle:
            key, _, remainder = line.partition(":")
            if key in {"MemTotal", "MemAvailable"}:
                values[key] = int(remainder.strip().split()[0]) * 1024
    total = values["MemTotal"]
    available = values["MemAvailable"]
    return total, max(0, total - available)


def host_metrics() -> dict[str, Any]:
    cpu: float | None = None
    total: int | None = None
    used: int | None = None
    try:
        before_total, before_idle = _proc_cpu_totals()
        time.sleep(0.12)
        after_total, after_idle = _proc_cpu_totals()
        delta_total = after_total - before_total
        delta_idle = after_idle - before_idle
        if delta_total > 0:
            cpu = round(max(0.0, min(100.0, (delta_total - delta_idle) * 100 / delta_total)), 1)
    except (OSError, ValueError, IndexError, KeyError):
        pass
    try:
        total, used = _host_memory()
    except (OSError, ValueError, KeyError, IndexError):
        pass
    return {
        "host_cpu_percent": cpu,
        "host_memory_total_bytes": total,
        "host_memory_used_bytes": used,
        "jvm_heap_used_bytes": None,
        "jvm_heap_max_bytes": None,
        "tps": None,
        "availability": {
            "host_cpu": "available" if cpu is not None else "unavailable",
            "host_memory": "available" if total is not None and used is not None else "unavailable",
            "jvm_memory": "unavailable",
            "tps": "unavailable",
        },
        "sampled_at": datetime.now(UTC).isoformat(),
    }


def server_logs(settings: Settings) -> dict[str, Any]:
    root = resolve_server_root(settings.server_dir)
    if root is None:
        return {"state": "unavailable", "lines": [], "reason": "Configure an existing server directory to read logs."}
    try:
        resolve_inside(root, settings.log_path)
        lines = read_bounded_tail(
            root,
            settings.log_path,
            max_bytes=256 * 1024,
            max_lines=settings.max_log_lines,
        )
        return {"state": "available", "lines": lines, "reason": None}
    except (UnsafeServerPath, OSError, ValueError):
        return {"state": "unavailable", "lines": [], "reason": "The configured log file is unavailable or outside the server directory."}


def mods_inventory(settings: Settings) -> dict[str, Any]:
    root = resolve_server_root(settings.server_dir)
    if root is None:
        return {"state": "unavailable", "items": [], "reason": "Configure an existing server directory to inspect mods."}
    try:
        resolve_inside(root, "mods", must_exist=False)
        items = []
        # Reopen by descriptor relative to the configured root. If the mods
        # path was replaced with a symlink after resolve_inside(), O_NOFOLLOW
        # rejects it. Individual entries are statted with follow_symlinks=False.
        for filename, size in list_regular_files(
            root, "mods", limit=settings.max_mod_entries
        ):
            items.append({"filename": _plain_text(filename, limit=255), "size_bytes": size})
        items.sort(key=lambda item: (item["filename"] or "").casefold())
        return {"state": "available", "items": items, "reason": None}
    except FileNotFoundError:
        # A Vanilla server may not have a mods directory.
        return {"state": "available", "items": [], "reason": None}
    except (UnsafeServerPath, OSError, ValueError):
        return {"state": "unavailable", "items": [], "reason": "The configured mods directory is unavailable or outside the server directory."}


def _server_root_for_testing(settings: Settings) -> Path | None:
    """Named seam for tests; normal API paths use the same validated resolver."""
    return resolve_server_root(settings.server_dir)
