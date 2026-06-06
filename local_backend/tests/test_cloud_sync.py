"""Tests for cloud synchronization wiring (events + SyncService + endpoint).

Run with::

    python -m unittest discover -s tests

These tests use the stdlib ``unittest`` so no extra dependency is required.
Each test runs against an isolated temporary SQLite database.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.config import config
from app.db.database import get_connection
from app.db.init_db import init_database
from app.integrations.cloud_client import CloudClient, CloudResult
from app.repositories.event_repository import EventRepository, EventSyncStatus
from app.services.sync_service import SyncService


class _FakeCloudClient:
    """In-memory CloudClient stand-in that records calls."""

    def __init__(self, *, available: bool = True, result: CloudResult | None = None):
        self._available = available
        self._result = result or CloudResult(ok=True, status_code=200, data={})
        self.sent_events: list = []

    def is_available(self) -> bool:
        return self._available

    def send_issue_event(self, event) -> CloudResult:
        self.sent_events.append(event)
        return self._result


class CloudSyncTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._original_db_path = config.db_path
        config.db_path = str(Path(self._tmpdir.name) / "test.db")
        self.addCleanup(self._restore_db_path)
        init_database()
        self.events = EventRepository()

    def _restore_db_path(self) -> None:
        config.db_path = self._original_db_path

    # ------------------------------------------------------------------
    # EventRepository
    # ------------------------------------------------------------------
    def test_event_created_with_local_event_id(self) -> None:
        event_id = self.events.create("SALE_STARTED", cell_number=3)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT local_event_id, sync_status FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()
        self.assertIsNotNone(row["local_event_id"])
        self.assertTrue(len(row["local_event_id"]) >= 8)
        self.assertEqual(row["sync_status"], EventSyncStatus.PENDING.value)

    def test_get_pending_returns_created_event(self) -> None:
        self.events.create("SALE_STARTED", cell_number=1)
        pending = self.events.get_pending_events()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].sync_status, EventSyncStatus.PENDING)

    # ------------------------------------------------------------------
    # SyncService
    # ------------------------------------------------------------------
    def test_pending_event_is_sent_to_cloud_client(self) -> None:
        self.events.create("SALE_STARTED", cell_number=1)
        fake = _FakeCloudClient()
        service = SyncService(cloud_client=fake, event_repository=self.events)

        summary = service.push_pending()

        self.assertEqual(len(fake.sent_events), 1)
        self.assertEqual(summary["sent"], 1)

    def test_success_marks_event_sent(self) -> None:
        self.events.create("SALE_STARTED", cell_number=1)
        fake = _FakeCloudClient(result=CloudResult(ok=True, status_code=200))
        service = SyncService(cloud_client=fake, event_repository=self.events)

        service.push_pending()

        with get_connection() as conn:
            statuses = [
                r["sync_status"]
                for r in conn.execute("SELECT sync_status FROM events").fetchall()
            ]
        self.assertEqual(statuses, [EventSyncStatus.SENT.value])

    def test_permanent_error_keeps_event_as_failed(self) -> None:
        self.events.create("SALE_STARTED", cell_number=1)
        fake = _FakeCloudClient(
            result=CloudResult(
                ok=False, status_code=400, error="VALIDATION_ERROR", retriable=False
            )
        )
        service = SyncService(cloud_client=fake, event_repository=self.events)

        summary = service.push_pending()

        self.assertEqual(summary["failed"], 1)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT sync_status, cloud_error_message FROM events"
            ).fetchone()
        # The event must NOT be deleted; it is kept with the error text.
        self.assertEqual(row["sync_status"], EventSyncStatus.FAILED.value)
        self.assertEqual(row["cloud_error_message"], "VALIDATION_ERROR")

    def test_transient_error_keeps_event_pending(self) -> None:
        self.events.create("SALE_STARTED", cell_number=1)
        fake = _FakeCloudClient(
            result=CloudResult(ok=False, error="timeout", retriable=True)
        )
        service = SyncService(cloud_client=fake, event_repository=self.events)

        summary = service.push_pending()

        self.assertEqual(summary["kept_pending"], 1)
        with get_connection() as conn:
            row = conn.execute("SELECT sync_status FROM events").fetchone()
        # Still pending, still present -> will be retried later.
        self.assertEqual(row["sync_status"], EventSyncStatus.PENDING.value)

    def test_sync_disabled_keeps_events_pending(self) -> None:
        self.events.create("SALE_STARTED", cell_number=1)
        fake = _FakeCloudClient(available=False)
        service = SyncService(cloud_client=fake, event_repository=self.events)

        summary = service.push_pending()

        self.assertFalse(summary["enabled"])
        self.assertEqual(len(fake.sent_events), 0)
        with get_connection() as conn:
            row = conn.execute("SELECT sync_status FROM events").fetchone()
        self.assertEqual(row["sync_status"], EventSyncStatus.PENDING.value)

    # ------------------------------------------------------------------
    # CloudClient network safety
    # ------------------------------------------------------------------
    def test_network_error_does_not_raise(self) -> None:
        # Unreachable address + tiny timeout: the call must return a
        # CloudResult, never raise, so FastAPI stays alive.
        client = CloudClient(
            base_url="http://127.0.0.1:9",
            token="dummy-token",
            timeout_seconds=0.5,
            enabled=True,
        )
        self.events.create("SALE_STARTED", cell_number=1)
        event = self.events.get_pending_events()[0]

        result = client.send_issue_event(event)

        self.assertIsInstance(result, CloudResult)
        self.assertFalse(result.ok)
        self.assertTrue(result.retriable)

    def test_push_pending_endpoint_returns_200(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import create_app
        from app.services.sync_service import get_sync_service

        self.events.create("SALE_STARTED", cell_number=1)
        fake = _FakeCloudClient()
        app = create_app()
        app.dependency_overrides[get_sync_service] = lambda: SyncService(
            cloud_client=fake, event_repository=self.events
        )

        with TestClient(app) as client:
            response = client.post("/api/sync/push-pending")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["sent"], 1)
        self.assertTrue(body["enabled"])


if __name__ == "__main__":
    unittest.main()
