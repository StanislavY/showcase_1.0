"""Business logic for sales (limit-bounded purchases from cells).

``SalesService`` is the single owner of the sales rules:

* an administrator sets a spending limit (in kopecks);
* a customer buys by pressing a cell button;
* a sale succeeds only after the hardware confirms the open command;
* every important event is recorded in the ``events`` table with
  ``sync_status = PENDING`` so a future cloud push can pick it up.

The service knows nothing about HTTP/FastAPI: it raises domain exceptions
that the thin router maps to HTTP codes and JSON bodies.

Hardware note
-------------
The existing USB layer is write-only: ``hardware.open_cell`` only reports
whether the open command was dispatched, not whether the cell physically
opened/closed. Per the current requirements a sale is considered done as
soon as ``open_cell`` returns success; we do NOT wait for a physical
close. This keeps the legacy ``HardwareClient`` untouched.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.domain.cell_status import CellStatus, LockStatus
from app.domain.event_types import EventType
from app.domain.layout import MAX_CELL_NUMBER, MIN_CELL_NUMBER
from app.hardware.hardware_client import get_hardware_client
from app.repositories.cell_repository import CellRecord, CellRepository
from app.repositories.event_repository import EventRepository
from app.repositories.sale_repository import SaleRecord, SaleRepository
from app.repositories.sales_limit_repository import (
    SalesLimitRecord,
    SalesLimitRepository,
)
from app.schemas.sales_schemas import (
    SaleResponse,
    SalesLimitSummaryResponse,
    SaleView,
)

logger = logging.getLogger(__name__)

_LIMIT_EXCEEDED_MESSAGE = "Ваш лимит закончился, обратитесь к администратору"
_NO_PRODUCT_MESSAGE = "Выберите ячейку, в которой есть товар"
_CELL_UNAVAILABLE_MESSAGE = "Ячейка сейчас недоступна. Выберите другую ячейку"
_HARDWARE_FAIL_MESSAGE = "Не удалось открыть ячейку. Обратитесь к администратору"
_NO_PRICE_MESSAGE = "У товара не указана цена"


# --------------------------------------------------------------------------
# Domain exceptions (the router maps them to HTTP codes)
# --------------------------------------------------------------------------
class SalesError(Exception):
    """Base exception for sales operations."""


class SalesValidationError(SalesError):
    """Invalid input, e.g. cell number out of range (HTTP 400)."""


class LimitExceededError(SalesError):
    """The sales limit is missing, exhausted or insufficient (HTTP 409)."""


class NoProductError(SalesError):
    """The cell holds no sellable product (HTTP 409)."""


class CellNotAvailableError(SalesError):
    """The cell is not closed / not available for sale (HTTP 409)."""


class ProductPriceError(SalesError):
    """The product has no valid price (HTTP 409)."""


class HardwareOpenError(SalesError):
    """The controller failed to open the cell (HTTP 503)."""


# --------------------------------------------------------------------------
# Hardware contract required by the service
# --------------------------------------------------------------------------
class _HardwarePort(Protocol):
    """Minimal hardware interface the sales service relies on."""

    def open_cell(self, cell_number: int) -> bool: ...


class SalesService:
    """Orchestrator of the sales workflow."""

    MIN_CELL_NUMBER: int = MIN_CELL_NUMBER
    MAX_CELL_NUMBER: int = MAX_CELL_NUMBER

    def __init__(
        self,
        hardware: _HardwarePort,
        *,
        cell_repository: CellRepository | None = None,
        limit_repository: SalesLimitRepository | None = None,
        sale_repository: SaleRepository | None = None,
        event_repository: EventRepository | None = None,
    ) -> None:
        self._hardware = hardware
        self._cells = cell_repository or CellRepository()
        self._limits = limit_repository or SalesLimitRepository()
        self._sales = sale_repository or SaleRepository()
        self._events = event_repository or EventRepository()

    # ------------------------------------------------------------------
    # Limit queries / administration
    # ------------------------------------------------------------------
    def get_current_limit_summary(self) -> SalesLimitSummaryResponse:
        """Return the active limit snapshot, or a NOT_SET placeholder."""
        active = self._limits.get_active_limit()
        if active is None:
            return SalesLimitSummaryResponse(
                limit_id=None,
                limit_amount_kopecks=0,
                sold_amount_kopecks=0,
                remaining_amount_kopecks=0,
                status="NOT_SET",
            )
        return _build_summary(active)

    def set_new_limit(
        self, limit_amount_kopecks: int
    ) -> SalesLimitSummaryResponse:
        """Close any active limit and open a fresh one (sold_amount = 0)."""
        if limit_amount_kopecks <= 0:
            raise SalesValidationError(
                "Лимит должен быть больше нуля."
            )

        self._limits.close_active_limit()
        new_limit = self._limits.create_new_limit(limit_amount_kopecks)

        self._events.add_event(
            EventType.SALES_LIMIT_SET.value,
            {
                "limit_id": new_limit.id,
                "limit_amount_kopecks": new_limit.limit_amount_kopecks,
            },
        )
        return _build_summary(new_limit)

    # ------------------------------------------------------------------
    # Sale scenario
    # ------------------------------------------------------------------
    def sell_from_cell(self, cell_number: int) -> SaleResponse:
        """Sell the product in ``cell_number`` if the limit allows it."""
        self._ensure_cell_number_in_range(cell_number)

        active_limit = self._limits.get_active_limit()
        if active_limit is None or active_limit.remaining_amount_kopecks <= 0:
            raise LimitExceededError(_LIMIT_EXCEEDED_MESSAGE)

        cell = self._get_cell_or_raise(cell_number)
        self._ensure_cell_has_product(cell)
        self._ensure_cell_closed(cell)

        price_kopecks = _price_to_kopecks(cell.product_price)
        if price_kopecks <= 0:
            raise ProductPriceError(_NO_PRICE_MESSAGE)
        if price_kopecks > active_limit.remaining_amount_kopecks:
            raise LimitExceededError(_LIMIT_EXCEEDED_MESSAGE)

        # product_* are guaranteed non-null by _ensure_cell_has_product.
        sale = self._sales.create_opening_sale(
            limit_id=active_limit.id,
            cell_number=cell_number,
            product_id=cell.product_id,  # type: ignore[arg-type]
            product_name=cell.product_name,  # type: ignore[arg-type]
            price_kopecks=price_kopecks,
        )
        self._events.add_event(
            EventType.SALE_STARTED.value,
            {
                "sale_id": sale.id,
                "limit_id": active_limit.id,
                "cell_number": cell_number,
                "product_id": cell.product_id,
                "product_name": cell.product_name,
                "price_kopecks": price_kopecks,
            },
            cell_number=cell_number,
            sale_id=sale.id,
        )

        dispatched = self._safe_open_cell(cell_number)
        if not dispatched:
            failed_sale = self._sales.fail_sale(
                sale.id, _HARDWARE_FAIL_MESSAGE
            )
            self._events.add_event(
                EventType.SALE_FAILED.value,
                {
                    "sale_id": failed_sale.id,
                    "limit_id": active_limit.id,
                    "cell_number": cell_number,
                    "reason": "open_command_not_dispatched",
                },
                cell_number=cell_number,
                sale_id=failed_sale.id,
            )
            # The cell and sold_amount are intentionally left unchanged.
            raise HardwareOpenError(_HARDWARE_FAIL_MESSAGE)

        # Success: the sale is counted only now, after open_cell succeeded.
        completed_sale = self._sales.complete_sale(sale.id)
        self._limits.increase_sold_amount(active_limit.id, price_kopecks)
        self._cells.update_status(
            cell_number,
            CellStatus.EMPTY,
            current_operation_id=None,
            clear_product=True,
        )

        summary = self.get_current_limit_summary()
        self._events.add_event(
            EventType.SALE_COMPLETED.value,
            {
                "sale_id": completed_sale.id,
                "limit_id": active_limit.id,
                "cell_number": cell_number,
                "product_id": completed_sale.product_id,
                "product_name": completed_sale.product_name,
                "price_kopecks": completed_sale.price_kopecks,
                "sold_amount_kopecks": summary.sold_amount_kopecks,
                "remaining_amount_kopecks": summary.remaining_amount_kopecks,
            },
            cell_number=cell_number,
            sale_id=completed_sale.id,
        )

        return SaleResponse(
            success=True,
            message="Ячейка открыта. Заберите товар.",
            sale=_sale_to_view(completed_sale),
            limit_summary=summary,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _safe_open_cell(self, cell_number: int) -> bool:
        try:
            return bool(self._hardware.open_cell(cell_number))
        except Exception as exc:  # noqa: BLE001 - never crash a sale on HW errors
            logger.exception(
                "open_cell(%s) raised in hardware layer: %s", cell_number, exc
            )
            return False

    def _ensure_cell_number_in_range(self, cell_number: int) -> None:
        if not (self.MIN_CELL_NUMBER <= cell_number <= self.MAX_CELL_NUMBER):
            raise SalesValidationError(
                f"Номер ячейки должен быть от "
                f"{self.MIN_CELL_NUMBER} до {self.MAX_CELL_NUMBER}."
            )

    def _get_cell_or_raise(self, cell_number: int) -> CellRecord:
        cell = self._cells.get_by_number(cell_number)
        if cell is None:
            raise SalesValidationError(f"Ячейка №{cell_number} не найдена.")
        return cell

    def _ensure_cell_has_product(self, cell: CellRecord) -> None:
        if (
            cell.status != CellStatus.LOADED
            or not cell.product_id
            or not cell.product_name
            or cell.product_price is None
        ):
            raise NoProductError(_NO_PRODUCT_MESSAGE)

    def _ensure_cell_closed(self, cell: CellRecord) -> None:
        # If the controller reports a real lock status, require CLOSED.
        # TODO: once the USB layer reports lock state, drop the UNKNOWN
        # allowance below and require CLOSED only.
        if cell.lock_status not in (LockStatus.CLOSED, LockStatus.UNKNOWN):
            raise CellNotAvailableError(_CELL_UNAVAILABLE_MESSAGE)


def _price_to_kopecks(product_price: float | None) -> int:
    """Convert a rouble price (stored as REAL) into integer kopecks."""
    if product_price is None:
        return 0
    return int(round(product_price * 100))


def _build_summary(record: SalesLimitRecord) -> SalesLimitSummaryResponse:
    return SalesLimitSummaryResponse(
        limit_id=record.id,
        limit_amount_kopecks=record.limit_amount_kopecks,
        sold_amount_kopecks=record.sold_amount_kopecks,
        remaining_amount_kopecks=record.remaining_amount_kopecks,
        status=record.status.value,
    )


def _sale_to_view(record: SaleRecord) -> SaleView:
    return SaleView(
        id=record.id,
        limit_id=record.limit_id,
        cell_number=record.cell_number,
        product_id=record.product_id,
        product_name=record.product_name,
        price_kopecks=record.price_kopecks,
        status=record.status.value,
        created_at=record.created_at,
        completed_at=record.completed_at,
        failed_at=record.failed_at,
        error_message=record.error_message,
    )


def get_sales_service() -> SalesService:
    """Factory used as a FastAPI dependency."""
    return SalesService(hardware=get_hardware_client())
