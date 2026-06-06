"""Business logic for the online-sales pickup ("Забрать товар") scenario.

``OnlineSalesService`` is the single owner of the online-sales pickup rules.
It is the Edge-Agent orchestrator for this flow:

* it asks the cloud whether the terminal is online and which cells to open;
* it opens those cells through the existing :class:`HardwareClient`;
* it records a local event per cell and forwards it to the cloud;
* if the cloud is temporarily unreachable *after* a cell was opened, the
  event is left ``PENDING`` so the background sync can deliver it later.

Design constraints honoured here:

* No HTTP/FastAPI concerns live in this module — the thin router maps the
  returned dict to a JSON response.
* The cloud is reached only through :class:`CloudClient`; the hardware only
  through :class:`HardwareClient`; events only through :class:`EventRepository`.
* The whole scenario is guarded by a non-blocking lock so a second button
  press while a pickup is running does not start a second pickup.

Hardware confirmation note
--------------------------
The legacy USB layer is write-only: ``hardware.open_cell`` reports only that
the open *command* was dispatched, not that the cell physically opened. Per
the current requirements a cell is considered "opened" as soon as the command
is dispatched successfully. We do NOT fabricate a physical confirmation.

TODO: once the controller can confirm the real lock state (see
``HardwareClient.get_lock_status`` / the Arduino protocol TODOs), gate the
``ISSUE_COMPLETED`` event below on that confirmation — and optionally send an
``OPEN_CONFIRMED`` event first — instead of trusting command dispatch alone.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Protocol

from app.domain.event_types import EventType
from app.hardware.hardware_client import get_hardware_client
from app.integrations.cloud_client import CloudClient, get_cloud_client
from app.repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)

# Response codes shared with the frontend (kept in one place on purpose).
CODE_IN_PROGRESS = "OPERATION_ALREADY_IN_PROGRESS"
CODE_CLOUD_UNAVAILABLE = "CLOUD_UNAVAILABLE"
CODE_NO_PRODUCTS = "NO_PRODUCTS_TO_PICKUP"
CODE_PICKUP_COMPLETED = "PICKUP_COMPLETED"
CODE_ISSUE_FAILED = "ISSUE_FAILED"
CODE_PICKUP_FAILED = "PICKUP_FAILED"

_MSG_IN_PROGRESS = "Выдача уже выполняется, пожалуйста подождите"
_NEXT_IN_PROGRESS = "Дождитесь завершения текущей операции"

_MSG_CLOUD_UNAVAILABLE = "Нет интернета, отсканируйте полученный QR-код"
_NEXT_CLOUD_UNAVAILABLE = (
    "Откройте QR-код получения на телефоне и поднесите его к сканеру"
)

_MSG_NO_PRODUCTS = "Нет товаров для выдачи"
_NEXT_NO_PRODUCTS = "Если вы недавно оплатили заказ, попробуйте чуть позже"

_MSG_PICKUP_COMPLETED = "Ячейки открыты. Заберите товар."

_NEXT_ISSUE_FAILED = "Обратитесь к администратору"

# A process-wide lock so the scenario cannot run twice concurrently, even
# though the service itself is created per request (FastAPI dependency).
_PICKUP_LOCK = threading.Lock()


class _HardwarePort(Protocol):
    """Minimal hardware interface this service relies on."""

    def open_cell(self, cell_number: int) -> bool: ...


class OnlineSalesService:
    """Orchestrator of the online-sales pickup workflow."""

    def __init__(
        self,
        *,
        cloud_client: CloudClient | None = None,
        hardware: _HardwarePort | None = None,
        event_repository: EventRepository | None = None,
        lock: "threading.Lock | None" = None,
    ) -> None:
        self._cloud = cloud_client or get_cloud_client()
        self._hardware = hardware or get_hardware_client()
        self._events = event_repository or EventRepository()
        self._lock = lock or _PICKUP_LOCK

    # ------------------------------------------------------------------
    # Public scenario
    # ------------------------------------------------------------------
    def pickup(self) -> dict:
        """Run the "Забрать товар" scenario once.

        Returns a plain dict ready to be serialized by the router. Never
        raises on network/hardware problems: every outcome is encoded in the
        returned body via ``success`` / ``code``.
        """
        if not self._lock.acquire(blocking=False):
            return {
                "success": False,
                "code": CODE_IN_PROGRESS,
                "message": _MSG_IN_PROGRESS,
                "next_action": _NEXT_IN_PROGRESS,
            }
        try:
            return self._run_pickup()
        finally:
            self._lock.release()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _run_pickup(self) -> dict:
        request_id = str(uuid.uuid4())

        # Step 2: connectivity check (local config + a real ping round-trip).
        if not self._cloud.is_available() or not self._cloud.ping(request_id).ok:
            return self._cloud_unavailable()

        # Step 3: ask the cloud which cells to open.
        start = self._cloud.pickup_start(request_id)
        if not start.ok:
            if start.retriable:
                return self._cloud_unavailable()
            return {
                "success": False,
                "code": CODE_PICKUP_FAILED,
                "message": start.error or "Не удалось начать выдачу",
                "next_action": _NEXT_ISSUE_FAILED,
            }

        cells = _extract_cells(start.data)
        if not cells:
            # Step 4: nothing to issue at this terminal right now.
            return {
                "success": False,
                "code": CODE_NO_PRODUCTS,
                "message": _MSG_NO_PRODUCTS,
                "next_action": _NEXT_NO_PRODUCTS,
            }

        # Step 5/4: open each cell, record + forward an event per cell.
        opened: list[int] = []
        failed: list[int] = []
        for cell in cells:
            cell_number = cell["cell_number"]
            issue_operation_id = cell.get("issue_operation_id")
            if self._safe_open_cell(cell_number):
                opened.append(cell_number)
                self._record_and_push(
                    EventType.ISSUE_COMPLETED.value,
                    cell_number=cell_number,
                    issue_operation_id=issue_operation_id,
                    payload={"source": "online_sales"},
                )
            else:
                failed.append(cell_number)
                self._record_and_push(
                    EventType.ISSUE_FAILED.value,
                    cell_number=cell_number,
                    issue_operation_id=issue_operation_id,
                    payload={
                        "source": "online_sales",
                        "reason": "open_command_not_dispatched",
                    },
                )

        return self._build_pickup_result(opened, failed)

    @staticmethod
    def _cloud_unavailable() -> dict:
        return {
            "success": False,
            "code": CODE_CLOUD_UNAVAILABLE,
            "message": _MSG_CLOUD_UNAVAILABLE,
            "next_action": _NEXT_CLOUD_UNAVAILABLE,
        }

    @staticmethod
    def _build_pickup_result(opened: list[int], failed: list[int]) -> dict:
        if failed:
            failed_str = ", ".join(str(n) for n in failed)
            return {
                "success": False,
                "code": CODE_ISSUE_FAILED,
                "message": f"Не удалось открыть ячейку(и): {failed_str}",
                "next_action": _NEXT_ISSUE_FAILED,
                "opened_cells": opened,
                "failed_cells": failed,
            }
        return {
            "success": True,
            "code": CODE_PICKUP_COMPLETED,
            "message": _MSG_PICKUP_COMPLETED,
            "opened_cells": opened,
            "failed_cells": failed,
        }

    def _safe_open_cell(self, cell_number: int) -> bool:
        """Dispatch an open command, never letting a HW error crash the flow.

        Returns True only if the command was dispatched successfully. This is
        the only "success" signal available today — see the module docstring
        and the TODO about real controller confirmation.
        """
        try:
            return bool(self._hardware.open_cell(cell_number))
        except Exception as exc:  # noqa: BLE001 - HW must never crash a pickup
            logger.exception(
                "open_cell(%s) raised in hardware layer: %s", cell_number, exc
            )
            return False

    def _record_and_push(
        self,
        event_type: str,
        *,
        cell_number: int,
        issue_operation_id: Any | None,
        payload: dict,
    ) -> None:
        """Create a local event (PENDING) and try to forward it to the cloud.

        On a cloud ACK the event is marked SENT; on a transient failure it is
        left PENDING for the background sync; on a permanent (4xx) rejection it
        is marked FAILED with the error text. The event row is never deleted.
        """
        body = dict(payload)
        if issue_operation_id is not None:
            body.setdefault("issue_operation_id", str(issue_operation_id))

        event_id = self._events.create(
            event_type, cell_number=cell_number, payload=body
        )
        record = self._events.get_by_id(event_id)
        if record is None:  # defensive: should not happen
            logger.error("event %s vanished right after creation", event_id)
            return

        result = self._cloud.send_issue_event(record)
        if result.ok:
            self._events.mark_sent(record.local_event_id)
        elif result.retriable:
            # Keep PENDING: the cell is already open, the cloud will catch up.
            logger.info(
                "event %s kept PENDING (cloud retriable): %s",
                record.local_event_id,
                result.error,
            )
        else:
            self._events.mark_failed(
                record.local_event_id, result.error or "cloud rejected event"
            )


def _extract_cells(cloud_data: Any) -> list[dict]:
    """Normalize the cloud ``pickup/start`` body into a list of cell dicts.

    Accepts both the unified cloud envelope (``{"data": {"cells": [...]}}``)
    and a bare list, and both integer cell numbers and per-cell dicts. Each
    returned item is guaranteed to have an integer ``cell_number``. Unknown
    shapes degrade to an empty list (treated as "no products").
    """
    inner = cloud_data
    if isinstance(cloud_data, dict):
        inner = cloud_data.get("data", cloud_data)

    raw_cells: Any = None
    if isinstance(inner, dict):
        raw_cells = inner.get("cells")
    elif isinstance(inner, list):
        raw_cells = inner

    if not isinstance(raw_cells, list):
        return []

    cells: list[dict] = []
    for item in raw_cells:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            cells.append({"cell_number": item})
        elif isinstance(item, dict):
            number = item.get("cell_number")
            if isinstance(number, int) and not isinstance(number, bool):
                cells.append(dict(item))
    return cells


def get_online_sales_service() -> OnlineSalesService:
    """Factory used as a FastAPI dependency (overridable in tests)."""
    return OnlineSalesService()
