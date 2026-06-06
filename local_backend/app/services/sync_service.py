"""Synchronization of local events with the cloud platform.

``SyncService`` is a small orchestrator that:

* reads PENDING events from the local SQLite log;
* pushes each one to the cloud via :class:`CloudClient`;
* on a cloud ACK marks the event SENT;
* on a transient (network/5xx) error leaves it PENDING for a later retry;
* on a permanent (4xx) error marks it FAILED with the error text.

Events are never deleted: the log stays auditable. The service never raises
on network problems – cloud failures are reflected in the returned summary.
"""

from __future__ import annotations

import logging

from app.integrations.cloud_client import CloudClient, get_cloud_client
from app.repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)


class SyncService:
    """Pushes pending local events to the cloud."""

    def __init__(
        self,
        *,
        cloud_client: CloudClient | None = None,
        event_repository: EventRepository | None = None,
    ) -> None:
        self._cloud = cloud_client or get_cloud_client()
        self._events = event_repository or EventRepository()

    def push_pending(self, limit: int = 100) -> dict:
        """Send pending events to the cloud and return a summary.

        The summary is a plain dict so the router can return it directly.
        """
        if not self._cloud.is_available():
            pending = self._events.get_pending_events(limit=limit)
            return {
                "enabled": False,
                "sent": 0,
                "failed": 0,
                "kept_pending": len(pending),
                "message": "Cloud sync disabled or not configured.",
            }

        pending = self._events.get_pending_events(limit=limit)
        sent = 0
        failed = 0
        kept_pending = 0

        for event in pending:
            result = self._cloud.send_issue_event(event)
            if result.ok:
                self._events.mark_sent(event.local_event_id)
                sent += 1
            elif result.retriable:
                # Transient failure: keep PENDING for the next sync attempt.
                kept_pending += 1
                logger.info(
                    "event %s kept PENDING (retriable): %s",
                    event.local_event_id,
                    result.error,
                )
            else:
                self._events.mark_failed(
                    event.local_event_id, result.error or "unknown error"
                )
                failed += 1

        return {
            "enabled": True,
            "sent": sent,
            "failed": failed,
            "kept_pending": kept_pending,
            "message": "Sync finished.",
        }


def get_sync_service() -> SyncService:
    """Factory used as a FastAPI dependency (overridable in tests)."""
    return SyncService()
