"""Tests for the online-sales pickup scenario ("Забрать товар").

Run with::

    python -m unittest discover -s tests

These tests use the stdlib ``unittest`` (no extra dependency) and an isolated
temporary SQLite database, mirroring ``test_cloud_sync.py``. The cloud and the
hardware are replaced by in-memory fakes so the scenario is exercised end to
end without a network or a USB device.
"""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from app.core.config import config
from app.db.database import get_connection
from app.db.init_db import init_database
from app.integrations.cloud_client import CloudResult
from app.repositories.event_repository import EventRepository, EventSyncStatus
from app.services.online_sales_service import (
    CODE_CLOUD_UNAVAILABLE,
    CODE_IN_PROGRESS,
    CODE_ISSUE_FAILED,
    CODE_NO_PRODUCTS,
    CODE_PICKUP_COMPLETED,
    OnlineSalesService,
)


def _envelope(cells) -> dict:
    """Build a cloud ``pickup/start`` body in the unified envelope shape."""
    return {"success": True, "code": "OK", "data": {"cells": cells}}


class _FakeCloudClient:
    """In-memory CloudClient stand-in with configurable behaviour."""

    def __init__(
        self,
        *,
        available: bool = True,
        ping_ok: bool = True,
        start_result: CloudResult | None = None,
        issue_result: CloudResult | None = None,
    ) -> None:
        self._available = available
        self._ping_ok = ping_ok
        self._start_result = start_result or CloudResult(
            ok=True, status_code=200, data=_envelope([])
        )
        self._issue_result = issue_result or CloudResult(
            ok=True, status_code=200, data={}
        )
        self.sent_events: list = []
        self.pickup_start_calls = 0

    def is_available(self) -> bool:
        return self._available

    def ping(self, request_id: str) -> CloudResult:
        return CloudResult(ok=self._ping_ok, status_code=200 if self._ping_ok else None,
                           retriable=not self._ping_ok)

    def pickup_start(self, request_id: str) -> CloudResult:
        self.pickup_start_calls += 1
        return self._start_result

    def send_issue_event(self, event) -> CloudResult:
        self.sent_events.append(event)
        return self._issue_result


class _FakeHardware:
    """Hardware stand-in that records opens and can fail selected cells."""

    def __init__(self, *, fail_cells: set[int] | None = None) -> None:
        self._fail_cells = fail_cells or set()
        self.opened: list[int] = []

    def open_cell(self, cell_number: int) -> bool:
        if cell_number in self._fail_cells:
            return False
        self.opened.append(cell_number)
        return True


class OnlineSalesPickupTestCase(unittest.TestCase):
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

    def _service(self, cloud, hardware) -> OnlineSalesService:
        # A fresh lock per service so tests do not interfere with each other.
        return OnlineSalesService(
            cloud_client=cloud,
            hardware=hardware,
            event_repository=self.events,
            lock=threading.Lock(),
        )

    def _event_rows(self) -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT event_type, cell_number, sync_status FROM events"
                " ORDER BY id"
            ).fetchall()

    # ------------------------------------------------------------------
    # 1. No cloud connection -> QR message
    # ------------------------------------------------------------------
    def test_cloud_not_configured_returns_qr_message(self) -> None:
        cloud = _FakeCloudClient(available=False)
        hardware = _FakeHardware()
        result = self._service(cloud, hardware).pickup()

        self.assertFalse(result["success"])
        self.assertEqual(result["code"], CODE_CLOUD_UNAVAILABLE)
        self.assertIn("QR", result["message"])
        self.assertEqual(cloud.pickup_start_calls, 0)
        self.assertEqual(hardware.opened, [])

    def test_cloud_ping_fails_returns_qr_message(self) -> None:
        cloud = _FakeCloudClient(available=True, ping_ok=False)
        hardware = _FakeHardware()
        result = self._service(cloud, hardware).pickup()

        self.assertFalse(result["success"])
        self.assertEqual(result["code"], CODE_CLOUD_UNAVAILABLE)
        self.assertEqual(cloud.pickup_start_calls, 0)

    # ------------------------------------------------------------------
    # 2. Re-press while running does not start a second pickup
    # ------------------------------------------------------------------
    def test_second_press_while_busy_is_rejected(self) -> None:
        cloud = _FakeCloudClient()
        hardware = _FakeHardware()
        lock = threading.Lock()
        service = OnlineSalesService(
            cloud_client=cloud,
            hardware=hardware,
            event_repository=self.events,
            lock=lock,
        )
        # Simulate an in-flight operation by holding the shared lock.
        self.assertTrue(lock.acquire(blocking=False))
        try:
            result = service.pickup()
        finally:
            lock.release()

        self.assertFalse(result["success"])
        self.assertEqual(result["code"], CODE_IN_PROGRESS)
        # The busy guard must short-circuit before any cloud call.
        self.assertEqual(cloud.pickup_start_calls, 0)

    # ------------------------------------------------------------------
    # 3. No products -> clear message
    # ------------------------------------------------------------------
    def test_no_products_returns_clear_message(self) -> None:
        cloud = _FakeCloudClient(
            start_result=CloudResult(ok=True, status_code=200, data=_envelope([]))
        )
        hardware = _FakeHardware()
        result = self._service(cloud, hardware).pickup()

        self.assertFalse(result["success"])
        self.assertEqual(result["code"], CODE_NO_PRODUCTS)
        self.assertEqual(hardware.opened, [])
        self.assertEqual(self._event_rows(), [])

    # ------------------------------------------------------------------
    # 4. Successful pickup -> cells opened + events created/sent
    # ------------------------------------------------------------------
    def test_successful_pickup_opens_cells_and_records_events(self) -> None:
        cells = [
            {"cell_number": 1, "issue_operation_id": "op-1"},
            {"cell_number": 5, "issue_operation_id": "op-5"},
        ]
        cloud = _FakeCloudClient(
            start_result=CloudResult(ok=True, status_code=200, data=_envelope(cells))
        )
        hardware = _FakeHardware()
        result = self._service(cloud, hardware).pickup()

        self.assertTrue(result["success"])
        self.assertEqual(result["code"], CODE_PICKUP_COMPLETED)
        self.assertEqual(result["opened_cells"], [1, 5])
        self.assertEqual(result["failed_cells"], [])
        self.assertEqual(hardware.opened, [1, 5])

        rows = self._event_rows()
        self.assertEqual(
            [(r["event_type"], r["cell_number"]) for r in rows],
            [("ISSUE_COMPLETED", 1), ("ISSUE_COMPLETED", 5)],
        )
        # Both events were ACKed by the (fake) cloud and marked SENT.
        self.assertEqual(
            [r["sync_status"] for r in rows],
            [EventSyncStatus.SENT.value, EventSyncStatus.SENT.value],
        )
        self.assertEqual(len(cloud.sent_events), 2)

    def test_successful_pickup_keeps_event_pending_when_cloud_down(self) -> None:
        # Cloud is reachable for ping + start, but the issue-event push fails
        # transiently *after* the cell is opened -> the event stays PENDING.
        cells = [{"cell_number": 3, "issue_operation_id": "op-3"}]
        cloud = _FakeCloudClient(
            start_result=CloudResult(ok=True, status_code=200, data=_envelope(cells)),
            issue_result=CloudResult(ok=False, error="timeout", retriable=True),
        )
        hardware = _FakeHardware()
        result = self._service(cloud, hardware).pickup()

        self.assertTrue(result["success"])
        self.assertEqual(hardware.opened, [3])
        rows = self._event_rows()
        self.assertEqual(rows[0]["sync_status"], EventSyncStatus.PENDING.value)

    # ------------------------------------------------------------------
    # 5. Open failure -> ISSUE_FAILED event + clear error with cell number
    # ------------------------------------------------------------------
    def test_open_failure_records_issue_failed_and_reports_cell(self) -> None:
        cells = [
            {"cell_number": 1, "issue_operation_id": "op-1"},
            {"cell_number": 5, "issue_operation_id": "op-5"},
        ]
        cloud = _FakeCloudClient(
            start_result=CloudResult(ok=True, status_code=200, data=_envelope(cells))
        )
        hardware = _FakeHardware(fail_cells={5})
        result = self._service(cloud, hardware).pickup()

        self.assertFalse(result["success"])
        self.assertEqual(result["code"], CODE_ISSUE_FAILED)
        self.assertIn("5", result["message"])
        self.assertEqual(result["opened_cells"], [1])
        self.assertEqual(result["failed_cells"], [5])

        rows = self._event_rows()
        by_cell = {r["cell_number"]: r["event_type"] for r in rows}
        self.assertEqual(by_cell[1], "ISSUE_COMPLETED")
        self.assertEqual(by_cell[5], "ISSUE_FAILED")

    # ------------------------------------------------------------------
    # Router wiring (thin endpoint returns the service body verbatim)
    # ------------------------------------------------------------------
    def test_pickup_endpoint_returns_service_body(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import create_app
        from app.services.online_sales_service import get_online_sales_service

        cells = [{"cell_number": 2, "issue_operation_id": "op-2"}]
        cloud = _FakeCloudClient(
            start_result=CloudResult(ok=True, status_code=200, data=_envelope(cells))
        )
        hardware = _FakeHardware()
        app = create_app()
        app.dependency_overrides[get_online_sales_service] = lambda: self._service(
            cloud, hardware
        )

        with TestClient(app) as client:
            response = client.post("/api/online-sales/pickup")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["opened_cells"], [2])


if __name__ == "__main__":
    unittest.main()
