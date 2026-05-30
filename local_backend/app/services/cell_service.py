"""Cell service: business logic for cell operations.

The service is the single owner of cell-related business rules:

* what cell numbers are valid for this postamat (1..27);
* whether the hardware is in a state where a command can be sent;
* how the result of a hardware call maps to a domain outcome.

It depends only on the hardware abstraction (``HardwareClient`` /
``MockHardwareClient``) and knows nothing about HTTP / FastAPI.
That keeps it easy to unit-test and reuse from other entry points
(WebSocket, CLI, scheduled tasks).
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.domain.layout import MAX_CELL_NUMBER, MIN_CELL_NUMBER
from app.hardware.hardware_client import get_hardware_client
from app.repositories.cell_repository import CellRecord, CellRepository
from app.schemas.cell_schemas import CellResponse

logger = logging.getLogger(__name__)


class _HardwarePort(Protocol):
    """Structural type the service relies on.

    Both ``HardwareClient`` and ``MockHardwareClient`` satisfy it.
    Declaring it explicitly documents the small contract the service
    actually needs and decouples it from concrete classes.
    """

    def is_available(self) -> bool: ...
    def open_cell(self, cell_number: int) -> bool: ...


class CellNumberOutOfRangeError(ValueError):
    """Raised when a requested cell number is outside the allowed range."""


class HardwareUnavailableError(RuntimeError):
    """Raised when the cell controller cannot accept commands right now."""


class CellService:
    """Cell business logic: opening via hardware and bookkeeping in SQLite."""

    MIN_CELL_NUMBER: int = MIN_CELL_NUMBER
    MAX_CELL_NUMBER: int = MAX_CELL_NUMBER

    def __init__(
        self,
        hardware: _HardwarePort,
        cell_repository: CellRepository | None = None,
    ) -> None:
        self._hardware = hardware
        self._cells = cell_repository or CellRepository()

    def list_cells(self) -> list[CellResponse]:
        """List all cells from the local DB (bookkeeping state)."""
        records = self._cells.list_all()
        return [_record_to_response(record) for record in records]

    def open_cell(self, cell_number: int) -> None:
        """Validate the cell number and send the open command."""
        self._ensure_cell_number_in_range(cell_number)

        if not self._hardware.is_available():
            logger.warning(
                "open_cell(%s) refused: hardware reports unavailable",
                cell_number,
            )
            raise HardwareUnavailableError("Контроллер ячеек недоступен")

        dispatched = self._hardware.open_cell(cell_number)
        if not dispatched:
            logger.error(
                "open_cell(%s) failed: hardware did not accept the command",
                cell_number,
            )
            raise HardwareUnavailableError("Контроллер ячеек недоступен")

    def _ensure_cell_number_in_range(self, cell_number: int) -> None:
        """Guard: cell number must be within the postamat layout."""
        if not (self.MIN_CELL_NUMBER <= cell_number <= self.MAX_CELL_NUMBER):
            raise CellNumberOutOfRangeError(
                f"Номер ячейки должен быть от "
                f"{self.MIN_CELL_NUMBER} до {self.MAX_CELL_NUMBER}"
            )


def _record_to_response(record: CellRecord) -> CellResponse:
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


def get_cell_service() -> CellService:
    """Factory used as a FastAPI dependency."""
    return CellService(hardware=get_hardware_client())
