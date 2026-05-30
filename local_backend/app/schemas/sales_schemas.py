"""Pydantic schemas for the sales workflow (limits and purchases).

All monetary amounts are integers in kopecks to avoid rounding errors.
The frontend converts them to roubles for display.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SalesLimitSummaryResponse(BaseModel):
    """Current sales-limit snapshot for the frontend."""

    limit_id: int | None = None
    limit_amount_kopecks: int = 0
    sold_amount_kopecks: int = 0
    remaining_amount_kopecks: int = 0
    status: str = "NOT_SET"


class SetSalesLimitRequest(BaseModel):
    """Admin request to set a new sales limit (in kopecks)."""

    limit_amount_kopecks: int = Field(
        ..., description="Лимит продаж в копейках, должен быть > 0"
    )


class SaleView(BaseModel):
    """A single sale as returned to the frontend."""

    id: int
    limit_id: int
    cell_number: int
    product_id: str
    product_name: str
    price_kopecks: int
    status: str
    created_at: str
    completed_at: str | None = None
    failed_at: str | None = None
    error_message: str | None = None


class SaleResponse(BaseModel):
    """Result of a sell-from-cell attempt."""

    success: bool
    message: str
    sale: SaleView | None = None
    limit_summary: SalesLimitSummaryResponse | None = None
