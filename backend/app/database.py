"""Minimal local SQLite schema for settings, event history, and backup metadata."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS dashboard_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS player_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK (event_type IN ('join', 'leave')),
    player_name TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_player_events_occurred_at ON player_events(occurred_at DESC);
CREATE TABLE IF NOT EXISTS backup_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    archive_path TEXT NOT NULL,
    size_bytes INTEGER,
    state TEXT NOT NULL,
    note TEXT
);
"""


def initialize_database(path: Path) -> None:
    """Create metadata tables; this does not create or copy a world backup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
