"""Initialization of the SQLite schema and seed data (27 cells)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.db.database import get_connection
from app.domain.cell_status import CellStatus
from app.domain.layout import MAX_CELL_NUMBER, MIN_CELL_NUMBER

_CREATE_CELLS = """
CREATE TABLE IF NOT EXISTS cells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL,
    product_id TEXT,
    product_name TEXT,
    product_price REAL,
    current_operation_id INTEGER,
    lock_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    last_lock_event_at TEXT,
    updated_at TEXT NOT NULL
);
"""

_CREATE_COURIER_OPERATIONS = """
CREATE TABLE IF NOT EXISTS courier_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    cell_number INTEGER NOT NULL,
    old_product_id TEXT,
    old_product_name TEXT,
    old_product_price REAL,
    new_product_id TEXT,
    new_product_name TEXT,
    new_product_price REAL,
    courier_id TEXT,
    error_message TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);
"""

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    local_event_id TEXT,
    event_type TEXT NOT NULL,
    cell_number INTEGER,
    operation_id INTEGER,
    sale_id INTEGER,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    sync_status TEXT NOT NULL,
    sent_at TEXT,
    cloud_error_message TEXT
);
"""

# A UNIQUE index (not a column constraint) lets us add the column to legacy
# tables: SQLite forbids ``ALTER TABLE ADD COLUMN ... UNIQUE``. Multiple NULLs
# are allowed, so partially-migrated rows do not clash.
_CREATE_EVENTS_LOCAL_ID_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_local_event_id
ON events (local_event_id);
"""

_CREATE_SALES_LIMITS = """
CREATE TABLE IF NOT EXISTS sales_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    limit_amount_kopecks INTEGER NOT NULL,
    sold_amount_kopecks INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);
"""

_CREATE_SALES = """
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    limit_id INTEGER NOT NULL,
    cell_number INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price_kopecks INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    failed_at TEXT,
    error_message TEXT
);
"""


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _create_tables(conn) -> None:
    conn.executescript(
        _CREATE_CELLS
        + _CREATE_COURIER_OPERATIONS
        + _CREATE_EVENTS
        + _CREATE_SALES_LIMITS
        + _CREATE_SALES
    )


def _migrate_cells(conn) -> None:
    """Add missing columns to an existing cells table.

    SQLite does not support ``ADD COLUMN IF NOT EXISTS``, so we inspect
    the actual set of columns via PRAGMA and add only the missing ones.
    This upgrades an old DB without losing data.
    """
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(cells)").fetchall()
    }
    if "lock_status" not in existing:
        conn.execute(
            "ALTER TABLE cells ADD COLUMN lock_status TEXT NOT NULL "
            "DEFAULT 'UNKNOWN'"
        )
    if "last_lock_event_at" not in existing:
        conn.execute(
            "ALTER TABLE cells ADD COLUMN last_lock_event_at TEXT"
        )


def _migrate_events(conn) -> None:
    """Add missing columns to an existing events table without data loss.

    Older databases may lack ``sale_id``, ``local_event_id`` or
    ``cloud_error_message``. SQLite has no ``ADD COLUMN IF NOT EXISTS``, so we
    inspect the columns first and add only what is missing. ``local_event_id``
    is then backfilled for legacy rows (so they can be synced) and a UNIQUE
    index is created.
    """
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(events)").fetchall()
    }
    if "sale_id" not in existing:
        conn.execute("ALTER TABLE events ADD COLUMN sale_id INTEGER")
    if "local_event_id" not in existing:
        # No UNIQUE here: SQLite rejects adding a UNIQUE column via ALTER.
        conn.execute("ALTER TABLE events ADD COLUMN local_event_id TEXT")
    if "cloud_error_message" not in existing:
        conn.execute("ALTER TABLE events ADD COLUMN cloud_error_message TEXT")

    # Backfill a stable, unique id for legacy rows that predate the column.
    conn.execute(
        "UPDATE events SET local_event_id = 'legacy-' || id "
        "WHERE local_event_id IS NULL"
    )
    conn.execute(_CREATE_EVENTS_LOCAL_ID_INDEX)


def _seed_cells(conn) -> None:
    """Create cells 1..27 with EMPTY status if they do not exist yet."""
    row = conn.execute("SELECT COUNT(*) AS cnt FROM cells").fetchone()
    if row["cnt"] >= MAX_CELL_NUMBER:
        return

    now = _utc_now_iso()
    for number in range(MIN_CELL_NUMBER, MAX_CELL_NUMBER + 1):
        conn.execute(
            """
            INSERT OR IGNORE INTO cells (number, status, updated_at)
            VALUES (?, ?, ?)
            """,
            (number, CellStatus.EMPTY.value, now),
        )


def init_database() -> None:
    """Create tables and seed the cells on application startup."""
    with get_connection() as conn:
        _create_tables(conn)
        _migrate_cells(conn)
        _migrate_events(conn)
        _seed_cells(conn)
