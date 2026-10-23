"""Validated environment configuration for the local dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ServerType = Literal["unknown", "vanilla", "neoforge", "forge", "fabric", "quilt", "paper", "purpur"]
SERVER_TYPES: tuple[ServerType, ...] = (
    "unknown", "vanilla", "neoforge", "forge", "fabric", "quilt", "paper", "purpur"
)


def _port(name: str, value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer port") from exc
    if not 1 <= parsed <= 65535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    bind_host: str = "127.0.0.1"
    port: int = 8000
    server_dir: Path | None = None
    server_host: str = "127.0.0.1"
    server_port: int = 25565
    server_name: str | None = None
    server_type: ServerType = "unknown"
    log_path: str = "logs/latest.log"
    db_path: Path = Path(__file__).resolve().parents[1] / "data" / "dashboard.sqlite3"
    status_timeout_seconds: float = 2.0
    max_log_lines: int = 200
    max_mod_entries: int = 500

    @classmethod
    def from_env(cls) -> "Settings":
        """Read only supported settings and reject unsafe or malformed values."""
        bind_host = os.environ.get("MCDASH_BIND_HOST", "127.0.0.1").strip()
        if bind_host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("MCDASH_BIND_HOST must be loopback (127.0.0.1, ::1, or localhost)")

        raw_type = os.environ.get("MCDASH_SERVER_TYPE", "unknown").strip().lower()
        if raw_type not in SERVER_TYPES:
            raise ValueError("MCDASH_SERVER_TYPE must be one of: " + ", ".join(SERVER_TYPES))

        raw_server_dir = os.environ.get("MCDASH_SERVER_DIR", "").strip()
        server_dir = Path(raw_server_dir).expanduser() if raw_server_dir else None

        log_path = os.environ.get("MCDASH_LOG_PATH", "logs/latest.log").strip()
        relative_log = Path(log_path)
        if not log_path or relative_log.is_absolute() or ".." in relative_log.parts:
            raise ValueError("MCDASH_LOG_PATH must be a relative path inside MCDASH_SERVER_DIR")

        db_raw = os.environ.get("MCDASH_DB_PATH", "").strip()
        db_path = (
            Path(db_raw).expanduser()
            if db_raw
            else Path(__file__).resolve().parents[1] / "data" / "dashboard.sqlite3"
        )

        timeout_raw = os.environ.get("MCDASH_STATUS_TIMEOUT", "2.0")
        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise ValueError("MCDASH_STATUS_TIMEOUT must be a number") from exc
        if not 0.1 <= timeout <= 10:
            raise ValueError("MCDASH_STATUS_TIMEOUT must be between 0.1 and 10 seconds")

        name = os.environ.get("MCDASH_SERVER_NAME", "").strip() or None
        if name is not None:
            name = _safe_label(name, limit=100)

        host = os.environ.get("MCDASH_SERVER_HOST", "127.0.0.1").strip()
        if not host or len(host) > 253 or any(ch.isspace() for ch in host):
            raise ValueError("MCDASH_SERVER_HOST must be a hostname or IP address")

        return cls(
            bind_host=bind_host,
            port=_port("MCDASH_PORT", os.environ.get("MCDASH_PORT", "8000")),
            server_dir=server_dir,
            server_host=host,
            server_port=_port("MCDASH_SERVER_PORT", os.environ.get("MCDASH_SERVER_PORT", "25565")),
            server_name=name,
            server_type=raw_type,  # type: ignore[arg-type]
            log_path=log_path,
            db_path=db_path,
            status_timeout_seconds=timeout,
        )


def _safe_label(value: str, *, limit: int) -> str:
    """Remove control characters from labels sourced from environment or server data."""
    return "".join(ch for ch in value if ch.isprintable())[:limit]
