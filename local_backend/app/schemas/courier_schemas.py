"""Pydantic schemas for courier operations.

They describe the request/response contracts of the courier service
operations. The router uses them as its only way of talking to the
outside world; all business logic lives in ``CourierOperationService``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.cell_status import CellStatus, LockStatus
from app.domain.courier_operation import (
    CourierOperationStatus,
    CourierOperationType,
)
from app.schemas.cell_schemas import CellResponse


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------
class LoadStartRequest(BaseModel):
    """Start loading a product into an empty cell."""

    # The 1..27 range is validated in the service as a business rule
    # (HTTP 400), so we deliberately omit ge/le here to avoid a technical 422.
    cell_number: int = Field(..., description="Номер ячейки (1..27)")
    product_id: str = Field(..., min_length=1, description="Идентификатор товара")
    product_name: str = Field(..., min_length=1, description="Название товара")
    product_price: float = Field(..., ge=0, description="Цена товара")
    courier_id: str | None = Field(None, description="Идентификатор курьера")


class UnloadStartRequest(BaseModel):
    """Start unloading a product from a loaded cell."""

    cell_number: int = Field(..., description="Номер ячейки (1..27)")
    courier_id: str | None = Field(None, description="Идентификатор курьера")


class ReplaceStartRequest(BaseModel):
    """Start replacing a product in a loaded cell."""

    cell_number: int = Field(..., description="Номер ячейки (1..27)")
    new_product_id: str = Field(..., min_length=1, description="Новый товар: id")
    new_product_name: str = Field(..., min_length=1, description="Новый товар: название")
    new_product_price: float = Field(..., ge=0, description="Новый товар: цена")
    courier_id: str | None = Field(None, description="Идентификатор курьера")


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class CourierOperationView(BaseModel):
    """Full state of a courier operation."""

    id: int
    operation_type: CourierOperationType
    status: CourierOperationStatus
    cell_number: int
    old_product_id: str | None = None
    old_product_name: str | None = None
    old_product_price: float | None = None
    new_product_id: str | None = None
    new_product_name: str | None = None
    new_product_price: float | None = None
    courier_id: str | None = None
    error_message: str | None = None
    started_at: str
    finished_at: str | None = None


class OperationStepResponse(BaseModel):
    """Response for workflow steps (start / refresh / action-done / cancel)."""

    operation_id: int
    operation_type: CourierOperationType
    operation_status: CourierOperationStatus
    cell_number: int
    cell_status: CellStatus
    lock_status: LockStatus
    message: str


class ConfirmResponse(BaseModel):
    """Operation completion response: the updated operation and cell."""

    message: str
    operation: CourierOperationView
    cell: CellResponse


class OperationStatusResponse(BaseModel):
    """Convenient operation-status DTO for the frontend."""

    operation_id: int
    operation_type: CourierOperationType
    operation_status: CourierOperationStatus
    cell_number: int
    cell_status: CellStatus
    lock_status: LockStatus
    message: str


class ErrorResponse(BaseModel):
    """Unified business-error format (human-readable message in Russian)."""

    detail: str = Field(..., description="Человекочитаемое сообщение об ошибке")


class MockCloseResponse(BaseModel):
    """Response of the dev endpoint that simulates closing a cell."""

    cell_number: int
    lock_status: LockStatus
    message: str
