"""Connection to the local postamat SQLite database."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import config


def get_db_path() -> Path:
    """Path to the DB file; the directory is created on initialization."""
    return Path(config.db_path)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Context-managed connection with row_factory = Row."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
