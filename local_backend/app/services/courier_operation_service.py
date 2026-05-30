"""Business logic for courier service operations.

``CourierOperationService`` is the single owner of the courier workflow
rules (load / unload / replace a product). It orchestrates:

* the repositories (cells, courier_operations, events);
* the hardware client (``HardwareClient`` / ``MockHardwareClient``).

The service knows nothing about HTTP/FastAPI and does not build HTTP
responses: it raises domain exceptions that the thin router maps to
response codes. This keeps the logic testable and reusable.

Key business rule: an operation cannot be completed until the controller
has confirmed that the lock is closed (``lock_status == CLOSED``).
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.domain.cell_status import CellStatus, LockStatus
from app.domain.courier_operation import (
    TERMINAL_OPERATION_STATUSES,
    CourierOperationStatus,
    CourierOperationType,
)
from app.domain.event_types import EventType
from app.domain.layout import MAX_CELL_NUMBER, MIN_CELL_NUMBER
from app.hardware.hardware_client import get_hardware_client
from app.repositories.cell_repository import CellRecord, CellRepository
from app.repositories.courier_operation_repository import (
    CourierOperationRecord,
    CourierOperationRepository,
)
from app.repositories.event_repository import EventRepository
from app.schemas.cell_schemas import CellResponse
from app.schemas.courier_schemas import (
    ConfirmResponse,
    CourierOperationView,
    LoadStartRequest,
    OperationStatusResponse,
    OperationStepResponse,
    ReplaceStartRequest,
    UnloadStartRequest,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Domain exceptions (the router maps them to HTTP codes)
# --------------------------------------------------------------------------
class CourierOperationError(Exception):
    """Base exception for courier operations."""


class OperationNotFoundError(CourierOperationError):
    """Operation not found (HTTP 404)."""


class BusinessRuleError(CourierOperationError):
    """A business rule was violated (HTTP 400)."""


class OperationConflictError(CourierOperationError):
    """Action is impossible in the current state (HTTP 409)."""


class HardwareUnavailableError(CourierOperationError):
    """The controller is unavailable or returned an error (HTTP 503)."""


# --------------------------------------------------------------------------
# Hardware contract required by the service
# --------------------------------------------------------------------------
class _HardwarePort(Protocol):
    """Minimal hardware interface the service relies on."""

    def is_available(self) -> bool: ...
    def open_cell(self, cell_number: int) -> bool: ...
    def get_lock_status(self, cell_number: int) -> LockStatus: ...


_STATUS_MESSAGES: dict[CourierOperationStatus, str] = {
    CourierOperationStatus.CREATED: (
        "Команда открытия отправлена. Ожидаем подтверждение открытия замка."
    ),
    CourierOperationStatus.CELL_OPEN_COMMAND_SENT: (
        "Команда открытия отправлена. Ожидаем подтверждение открытия замка."
    ),
    CourierOperationStatus.WAITING_CELL_OPEN: (
        "Команда открытия отправлена. Ожидаем подтверждение открытия замка."
    ),
    CourierOperationStatus.WAITING_COURIER_ACTION: (
        "Ячейка открыта. Выполните действие с товаром."
    ),
    CourierOperationStatus.WAITING_CELL_CLOSE: (
        "Закройте ячейку. Ожидаем подтверждение закрытия замка."
    ),
    CourierOperationStatus.READY_TO_CONFIRM: (
        "Ячейка закрыта. Можно завершить операцию."
    ),
    CourierOperationStatus.COMPLETED: "Операция завершена.",
    CourierOperationStatus.CANCELLED: "Операция отменена.",
    CourierOperationStatus.FAILED: "Операция завершилась ошибкой.",
}


class CourierOperationService:
    """Orchestrator of courier service operations."""

    MIN_CELL_NUMBER: int = MIN_CELL_NUMBER
    MAX_CELL_NUMBER: int = MAX_CELL_NUMBER

    def __init__(
        self,
        hardware: _HardwarePort,
        *,
        cell_repository: CellRepository | None = None,
        operation_repository: CourierOperationRepository | None = None,
        event_repository: EventRepository | None = None,
    ) -> None:
        self._hardware = hardware
        self._cells = cell_repository or CellRepository()
        self._operations = operation_repository or CourierOperationRepository()
        self._events = event_repository or EventRepository()

    # ------------------------------------------------------------------
    # Public start scenarios
    # ------------------------------------------------------------------
    def start_load(self, request: LoadStartRequest) -> OperationStepResponse:
        return self._start(
            operation_type=CourierOperationType.LOAD,
            cell_number=request.cell_number,
            required_status=CellStatus.EMPTY,
            courier_id=request.courier_id,
            new_product_id=request.product_id,
            new_product_name=request.product_name,
            new_product_price=request.product_price,
            started_event=EventType.LOAD_STARTED,
        )

    def start_unload(self, request: UnloadStartRequest) -> OperationStepResponse:
        cell = self._get_cell_or_raise(request.cell_number)
        return self._start(
            operation_type=CourierOperationType.UNLOAD,
            cell_number=request.cell_number,
            required_status=CellStatus.LOADED,
            courier_id=request.courier_id,
            old_product_id=cell.product_id,
            old_product_name=cell.product_name,
            old_product_price=cell.product_price,
            started_event=EventType.UNLOAD_STARTED,
            preloaded_cell=cell,
        )

    def start_replace(self, request: ReplaceStartRequest) -> OperationStepResponse:
        cell = self._get_cell_or_raise(request.cell_number)
        return self._start(
            operation_type=CourierOperationType.REPLACE,
            cell_number=request.cell_number,
            required_status=CellStatus.LOADED,
            courier_id=request.courier_id,
            old_product_id=cell.product_id,
            old_product_name=cell.product_name,
            old_product_price=cell.product_price,
            new_product_id=request.new_product_id,
            new_product_name=request.new_product_name,
            new_product_price=request.new_product_price,
            started_event=EventType.REPLACE_STARTED,
            preloaded_cell=cell,
        )

    def _start(
        self,
        *,
        operation_type: CourierOperationType,
        cell_number: int,
        required_status: CellStatus,
        started_event: EventType,
        courier_id: str | None = None,
        old_product_id: str | None = None,
        old_product_name: str | None = None,
        old_product_price: float | None = None,
        new_product_id: str | None = None,
        new_product_name: str | None = None,
        new_product_price: float | None = None,
        preloaded_cell: CellRecord | None = None,
    ) -> OperationStepResponse:
        """Shared operation-start scenario (DRY for load/unload/replace)."""
        self._ensure_cell_number_in_range(cell_number)
        cell = preloaded_cell or self._get_cell_or_raise(cell_number)

        self._ensure_cell_status(cell, required_status, operation_type)
        self._ensure_lock_ready_to_open(cell)

        operation_id = self._operations.create(
            operation_type,
            cell_number,
            courier_id=courier_id,
            old_product_id=old_product_id,
            old_product_name=old_product_name,
            old_product_price=old_product_price,
            new_product_id=new_product_id,
            new_product_name=new_product_name,
            new_product_price=new_product_price,
        )
        self._log(started_event, cell_number, operation_id, {
            "operation_type": operation_type.value,
        })

        # The cell moves to SERVICE; the product is kept as-is (for
        # UNLOAD/REPLACE it physically stays in the cell until confirm/cancel).
        self._cells.update_status(
            cell_number,
            CellStatus.SERVICE,
            product_id=cell.product_id,
            product_name=cell.product_name,
            product_price=cell.product_price,
            current_operation_id=operation_id,
        )

        dispatched = self._safe_open_cell(cell_number)
        if not dispatched:
            self._fail_open(operation_id, cell_number)
            raise HardwareUnavailableError(
                "Контроллер ячеек недоступен. Команда открытия не отправлена."
            )

        self._operations.update_status(
            operation_id, CourierOperationStatus.WAITING_CELL_OPEN
        )
        self._log(
            EventType.CELL_OPEN_COMMAND_SENT, cell_number, operation_id, {}
        )

        refreshed_cell = self._get_cell_or_raise(cell_number)
        return OperationStepResponse(
            operation_id=operation_id,
            operation_type=operation_type,
            operation_status=CourierOperationStatus.WAITING_CELL_OPEN,
            cell_number=cell_number,
            cell_status=refreshed_cell.status,
            lock_status=refreshed_cell.lock_status,
            message=(
                "Команда открытия отправлена. "
                "Ожидаем подтверждение открытия замка."
            ),
        )

    # ------------------------------------------------------------------
    # Workflow progression
    # ------------------------------------------------------------------
    def refresh_lock_status(self, operation_id: int) -> OperationStepResponse:
        """Read the lock status from the controller and advance the operation."""
        operation = self._get_operation_or_raise(operation_id)
        cell = self._get_cell_or_raise(operation.cell_number)

        lock_status = self._hardware.get_lock_status(operation.cell_number)
        self._cells.update_lock_status(operation.cell_number, lock_status)
        self._log(
            EventType.LOCK_STATUS_UPDATED,
            operation.cell_number,
            operation_id,
            {"lock_status": lock_status.value},
        )

        message: str
        new_status = operation.status

        if lock_status == LockStatus.ERROR:
            self._operations.update_status(
                operation_id,
                CourierOperationStatus.FAILED,
                error_message="Контроллер сообщил об ошибке замка.",
                finished=True,
            )
            self._cells.update_status(
                operation.cell_number,
                CellStatus.ERROR,
                product_id=cell.product_id,
                product_name=cell.product_name,
                product_price=cell.product_price,
                current_operation_id=operation_id,
            )
            self._log(
                EventType.CELL_ERROR, operation.cell_number, operation_id, {}
            )
            raise HardwareUnavailableError(
                "Ошибка замка ячейки. Операция переведена в FAILED."
            )

        if (
            operation.status == CourierOperationStatus.WAITING_CELL_OPEN
            and lock_status == LockStatus.OPEN
        ):
            new_status = CourierOperationStatus.WAITING_COURIER_ACTION
            self._operations.update_status(operation_id, new_status)
            self._log(
                EventType.CELL_OPENED, operation.cell_number, operation_id, {}
            )
            message = "Ячейка открыта. Выполните действие с товаром."
        elif (
            operation.status == CourierOperationStatus.WAITING_CELL_CLOSE
            and lock_status == LockStatus.CLOSED
        ):
            new_status = CourierOperationStatus.READY_TO_CONFIRM
            self._operations.update_status(operation_id, new_status)
            self._log(
                EventType.CELL_CLOSED, operation.cell_number, operation_id, {}
            )
            message = "Ячейка закрыта. Можно завершить операцию."
        else:
            message = _STATUS_MESSAGES.get(operation.status, operation.status.value)

        refreshed_cell = self._get_cell_or_raise(operation.cell_number)
        return OperationStepResponse(
            operation_id=operation_id,
            operation_type=operation.operation_type,
            operation_status=new_status,
            cell_number=operation.cell_number,
            cell_status=refreshed_cell.status,
            lock_status=refreshed_cell.lock_status,
            message=message,
        )

    def courier_action_done(self, operation_id: int) -> OperationStepResponse:
        """The courier reports that they placed/took/replaced the product."""
        operation = self._get_operation_or_raise(operation_id)
        cell = self._get_cell_or_raise(operation.cell_number)

        if operation.status != CourierOperationStatus.WAITING_COURIER_ACTION:
            raise OperationConflictError(
                "Действие недоступно: ожидается состояние "
                "«ячейка открыта, ждём действие курьера»."
            )
        if cell.lock_status != LockStatus.OPEN:
            raise OperationConflictError(
                "Ячейка ещё не открыта. Дождитесь открытия замка."
            )

        self._operations.update_status(
            operation_id, CourierOperationStatus.WAITING_CELL_CLOSE
        )
        self._log(
            EventType.COURIER_ACTION_DONE, operation.cell_number, operation_id, {}
        )

        return OperationStepResponse(
            operation_id=operation_id,
            operation_type=operation.operation_type,
            operation_status=CourierOperationStatus.WAITING_CELL_CLOSE,
            cell_number=operation.cell_number,
            cell_status=cell.status,
            lock_status=cell.lock_status,
            message="Закройте ячейку. Ожидаем подтверждение закрытия замка.",
        )

    def confirm(self, operation_id: int) -> ConfirmResponse:
        """Complete the operation after a confirmed lock closure."""
        operation = self._get_operation_or_raise(operation_id)
        cell = self._get_cell_or_raise(operation.cell_number)

        if operation.status != CourierOperationStatus.READY_TO_CONFIRM:
            raise OperationConflictError(
                "Операцию нельзя завершить, пока ячейка не закрыта."
            )
        if cell.lock_status != LockStatus.CLOSED:
            raise OperationConflictError(
                "Операцию нельзя завершить, пока ячейка не закрыта."
            )

        if operation.operation_type == CourierOperationType.LOAD:
            self._cells.update_status(
                operation.cell_number,
                CellStatus.LOADED,
                product_id=operation.new_product_id,
                product_name=operation.new_product_name,
                product_price=operation.new_product_price,
                current_operation_id=None,
            )
            event = EventType.PRODUCT_LOADED
        elif operation.operation_type == CourierOperationType.UNLOAD:
            self._cells.update_status(
                operation.cell_number,
                CellStatus.EMPTY,
                current_operation_id=None,
                clear_product=True,
            )
            event = EventType.PRODUCT_UNLOADED
        else:  # REPLACE
            self._cells.update_status(
                operation.cell_number,
                CellStatus.LOADED,
                product_id=operation.new_product_id,
                product_name=operation.new_product_name,
                product_price=operation.new_product_price,
                current_operation_id=None,
            )
            event = EventType.PRODUCT_REPLACED

        self._operations.update_status(
            operation_id, CourierOperationStatus.COMPLETED, finished=True
        )
        self._log(event, operation.cell_number, operation_id, {
            "operation_type": operation.operation_type.value,
        })

        final_operation = self._get_operation_or_raise(operation_id)
        final_cell = self._get_cell_or_raise(operation.cell_number)
        return ConfirmResponse(
            message="Операция успешно завершена.",
            operation=_to_view(final_operation),
            cell=_cell_to_response(final_cell),
        )

    def cancel(self, operation_id: int) -> OperationStepResponse:
        """Cancel an unfinished operation (only when the cell is closed)."""
        operation = self._get_operation_or_raise(operation_id)
        cell = self._get_cell_or_raise(operation.cell_number)

        if operation.status in TERMINAL_OPERATION_STATUSES:
            raise OperationConflictError(
                "Операцию нельзя отменить: она уже завершена."
            )
        if cell.lock_status == LockStatus.OPEN:
            raise OperationConflictError(
                "Нельзя отменить операцию, пока ячейка открыта. Закройте ячейку."
            )

        if operation.operation_type == CourierOperationType.LOAD:
            self._cells.update_status(
                operation.cell_number,
                CellStatus.EMPTY,
                current_operation_id=None,
                clear_product=True,
            )
        else:  # UNLOAD / REPLACE — restore the old product
            self._cells.update_status(
                operation.cell_number,
                CellStatus.LOADED,
                product_id=operation.old_product_id,
                product_name=operation.old_product_name,
                product_price=operation.old_product_price,
                current_operation_id=None,
            )

        self._operations.update_status(
            operation_id, CourierOperationStatus.CANCELLED, finished=True
        )
        self._log(
            EventType.OPERATION_CANCELLED, operation.cell_number, operation_id, {}
        )

        refreshed_cell = self._get_cell_or_raise(operation.cell_number)
        return OperationStepResponse(
            operation_id=operation_id,
            operation_type=operation.operation_type,
            operation_status=CourierOperationStatus.CANCELLED,
            cell_number=operation.cell_number,
            cell_status=refreshed_cell.status,
            lock_status=refreshed_cell.lock_status,
            message="Операция отменена.",
        )

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------
    def get_operation(self, operation_id: int) -> CourierOperationView:
        return _to_view(self._get_operation_or_raise(operation_id))

    def list_active(self) -> list[CourierOperationView]:
        return [_to_view(record) for record in self._operations.list_active()]

    def get_status(self, operation_id: int) -> OperationStatusResponse:
        operation = self._get_operation_or_raise(operation_id)
        cell = self._get_cell_or_raise(operation.cell_number)
        return OperationStatusResponse(
            operation_id=operation.id,
            operation_type=operation.operation_type,
            operation_status=operation.status,
            cell_number=operation.cell_number,
            cell_status=cell.status,
            lock_status=cell.lock_status,
            message=_STATUS_MESSAGES.get(operation.status, operation.status.value),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _safe_open_cell(self, cell_number: int) -> bool:
        if not self._hardware.is_available():
            logger.warning(
                "open_cell(%s) refused: hardware unavailable", cell_number
            )
            return False
        return bool(self._hardware.open_cell(cell_number))

    def _fail_open(self, operation_id: int, cell_number: int) -> None:
        """Roll back state when the open command could not be dispatched."""
        cell = self._cells.get_by_number(cell_number)
        self._operations.update_status(
            operation_id,
            CourierOperationStatus.FAILED,
            error_message="Команда открытия ячейки не отправлена.",
            finished=True,
        )
        self._cells.update_status(
            cell_number,
            CellStatus.ERROR,
            product_id=cell.product_id if cell else None,
            product_name=cell.product_name if cell else None,
            product_price=cell.product_price if cell else None,
            current_operation_id=operation_id,
        )
        self._cells.update_lock_status(cell_number, LockStatus.ERROR)
        self._log(EventType.OPERATION_FAILED, cell_number, operation_id, {
            "reason": "open_command_not_dispatched",
        })

    def _ensure_cell_number_in_range(self, cell_number: int) -> None:
        if not (self.MIN_CELL_NUMBER <= cell_number <= self.MAX_CELL_NUMBER):
            raise BusinessRuleError(
                f"Номер ячейки должен быть от "
                f"{self.MIN_CELL_NUMBER} до {self.MAX_CELL_NUMBER}."
            )

    def _ensure_cell_status(
        self,
        cell: CellRecord,
        required: CellStatus,
        operation_type: CourierOperationType,
    ) -> None:
        if cell.status == required:
            return
        if operation_type == CourierOperationType.LOAD:
            raise BusinessRuleError(
                f"Загрузка невозможна: ячейка №{cell.number} должна быть "
                f"пустой (EMPTY), а сейчас {cell.status.value}."
            )
        raise BusinessRuleError(
            f"Операция невозможна: ячейка №{cell.number} должна быть "
            f"загружена (LOADED), а сейчас {cell.status.value}."
        )

    def _ensure_lock_ready_to_open(self, cell: CellRecord) -> None:
        if cell.lock_status not in (LockStatus.CLOSED, LockStatus.UNKNOWN):
            raise BusinessRuleError(
                f"Операция невозможна: замок ячейки №{cell.number} в "
                f"состоянии {cell.lock_status.value}. Ожидается CLOSED или "
                f"UNKNOWN."
            )

    def _get_cell_or_raise(self, cell_number: int) -> CellRecord:
        cell = self._cells.get_by_number(cell_number)
        if cell is None:
            raise BusinessRuleError(f"Ячейка №{cell_number} не найдена.")
        return cell

    def _get_operation_or_raise(self, operation_id: int) -> CourierOperationRecord:
        operation = self._operations.get_by_id(operation_id)
        if operation is None:
            raise OperationNotFoundError(
                f"Операция №{operation_id} не найдена."
            )
        return operation

    def _log(
        self,
        event_type: EventType,
        cell_number: int | None,
        operation_id: int | None,
        payload: dict,
    ) -> None:
        self._events.create(
            event_type.value,
            cell_number=cell_number,
            operation_id=operation_id,
            payload=payload,
        )


def _to_view(record: CourierOperationRecord) -> CourierOperationView:
    return CourierOperationView(
        id=record.id,
        operation_type=record.operation_type,
        status=record.status,
        cell_number=record.cell_number,
        old_product_id=record.old_product_id,
        old_product_name=record.old_product_name,
        old_product_price=record.old_product_price,
        new_product_id=record.new_product_id,
        new_product_name=record.new_product_name,
        new_product_price=record.new_product_price,
        courier_id=record.courier_id,
        error_message=record.error_message,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )


def _cell_to_response(record: CellRecord) -> CellResponse:
    return CellResponse(
        number=record.number,
        status=record.status.value,
        product_id=record.product_id,
        product_name=record.product_name,
        product_price=record.product_price,
        lock_status=record.lock_status.value,
        last_lock_event_at=record.last_lock_event_at,
        updated_at=record.updated_at,
    )


def get_courier_operation_service() -> CourierOperationService:
    """Factory used as a FastAPI dependency."""
    return CourierOperationService(hardware=get_hardware_client())
