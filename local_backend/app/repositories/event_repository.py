"""Event repository for the log and future cloud synchronization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.db.database import get_connection


class EventSyncStatus(StrEnum):
    """Status of sending an event to an external system."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


@dataclass(frozen=True)
class EventRecord:
    """A row of the events table."""

    id: int
    event_type: str
    cell_number: int | None
    operation_id: int | None
    sale_id: int | None
    payload_json: str
    created_at: str
    sync_status: EventSyncStatus
    sent_at: str | None


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
        """Add an event with sync status PENDING."""
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    event_type, cell_number, operation_id, sale_id,
                    payload_json, created_at, sync_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
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
