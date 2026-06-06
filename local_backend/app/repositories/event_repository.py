"""Event repository for the log and future cloud synchronization."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.db.database import get_connection


class EventSyncStatus(StrEnum):
    """Status of sending an event to an external system."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


_EVENT_COLUMNS = """
    id, local_event_id, event_type, cell_number, operation_id, sale_id,
    payload_json, created_at, sync_status, sent_at, cloud_error_message
"""


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class EventRecord:
    """A row of the events table."""

    id: int
    local_event_id: str | None
    event_type: str
    cell_number: int | None
    operation_id: int | None
    sale_id: int | None
    payload_json: str
    created_at: str
    sync_status: EventSyncStatus
    sent_at: str | None
    cloud_error_message: str | None

    @property
    def payload(self) -> dict:
        """The decoded payload, or an empty dict on bad/empty JSON."""
        try:
            data = json.loads(self.payload_json or "{}")
        except (ValueError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}


class EventRepository:
    """Writes events to the local log."""

    def create(
        self,
        event_type: str,
        *,
        cell_number: int | None = None,
        operation_id: int | None = None,
        sale_id: int | None = None,
        payload: dict | None = None,
    ) -> int:
        """Add an event with sync status PENDING.

        Every event gets a unique ``local_event_id`` (UUID4) used as the
        idempotency key when pushing the event to the cloud.
        """
        now = _utc_now_iso()
        local_event_id = str(uuid.uuid4())
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    local_event_id, event_type, cell_number, operation_id,
                    sale_id, payload_json, created_at, sync_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    local_event_id,
                    event_type,
                    cell_number,
                    operation_id,
                    sale_id,
                    payload_json,
                    now,
                    EventSyncStatus.PENDING.value,
                ),
            )
            return int(cursor.lastrowid)

    def add_event(
        self,
        event_type: str,
        payload: dict | None = None,
        *,
        cell_number: int | None = None,
        operation_id: int | None = None,
        sale_id: int | None = None,
    ) -> int:
        """Convenience alias used by the sales workflow.

        Records an event with ``sync_status = PENDING`` so it is ready for a
        future push to an external server (not implemented at this stage).
        """
        return self.create(
            event_type,
            cell_number=cell_number,
            operation_id=operation_id,
            sale_id=sale_id,
            payload=payload,
        )

    # ------------------------------------------------------------------
    # Cloud synchronization support
    # ------------------------------------------------------------------
    def get_by_id(self, event_id: int) -> EventRecord | None:
        """Return a single event by its primary key, or ``None`` if absent."""
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT {_EVENT_COLUMNS} FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()
        return _row_to_record(row) if row is not None else None

    def get_pending_events(self, limit: int = 100) -> list[EventRecord]:
        """Return events still waiting to be sent to the cloud (oldest first)."""
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_EVENT_COLUMNS}
                FROM events
                WHERE sync_status = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (EventSyncStatus.PENDING.value, limit),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def mark_sent(self, local_event_id: str) -> None:
        """Mark an event as successfully delivered (SENT), clearing errors."""
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE events
                SET sync_status = ?, sent_at = ?, cloud_error_message = NULL
                WHERE local_event_id = ?
                """,
                (
                    EventSyncStatus.SENT.value,
                    _utc_now_iso(),
                    local_event_id,
                ),
            )

    def mark_failed(self, local_event_id: str, error_message: str) -> None:
        """Mark an event as permanently FAILED, keeping the error text.

        The event row is never deleted, so failures remain auditable and can
        be retried later if needed.
        """
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE events
                SET sync_status = ?, cloud_error_message = ?
                WHERE local_event_id = ?
                """,
                (
                    EventSyncStatus.FAILED.value,
                    error_message,
                    local_event_id,
                ),
            )


def _row_to_record(row) -> EventRecord:
    return EventRecord(
        id=int(row["id"]),
        local_event_id=row["local_event_id"],
        event_type=row["event_type"],
        cell_number=row["cell_number"],
        operation_id=row["operation_id"],
        sale_id=row["sale_id"],
        payload_json=row["payload_json"],
        created_at=row["created_at"],
        sync_status=EventSyncStatus(row["sync_status"]),
        sent_at=row["sent_at"],
        cloud_error_message=row["cloud_error_message"],
    )
