from pathlib import Path
import sqlite3

from app.database import initialize_database


def test_metadata_schema_initializes_without_world_backup(tmp_path: Path) -> None:
    db = tmp_path / "dashboard.sqlite3"
    initialize_database(db)
    initialize_database(db)
    with sqlite3.connect(db) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"dashboard_config", "player_events", "backup_metadata"}.issubset(tables)
