"""Pydantic schemas for cell-related API contracts.

Schemas describe the shape of JSON returned by ``/api/cells`` endpoints.
They intentionally mirror the contract documented in the project spec
so the frontend can rely on a stable structure for both success and
error cases.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.cell_status import CellStatus, LockStatus

# Possible values of ``OpenCellResponse.status``.
#
# IMPORTANT: today the cell controller protocol used by this project is
# write-only — the backend sends an "open" command and never reads back
# whether the cell physically opened. Therefore we deliberately do NOT
# expose ``"open"`` / ``"closed"`` here: it would imply confirmation we
# cannot give. The only honest post-dispatch state is ``"command_sent"``.
#
# TODO: Wire up real cell-status reading from the controller here. Once
# the protocol gains a response side, extend this Literal with values
# like "open" / "closed" / "timeout" and propagate them from CellService.
CellOpenStatus = Literal["command_sent", "dispatch_failed"]


class CellResponse(BaseModel):
    """Postamat cell for ``GET /api/cells`` (bookkeeping state in SQLite)."""

    number: int = Field(..., description="Номер ячейки (1..27)")
    status: CellStatus = Field(..., description="Статус ячейки в учёте")
    product_id: str | None = Field(None, description="Идентификатор товара в ячейке")
    product_name: str | None = Field(None, description="Название товара")
    product_price: float | None = Field(None, description="Цена товара")
    lock_status: LockStatus = Field(
        LockStatus.UNKNOWN, description="Доменный статус замка ячейки"
    )
    last_lock_event_at: str | None = Field(
        None, description="Время последнего события замка (ISO 8601, UTC)"
    )
    updated_at: str = Field(..., description="Время последнего изменения (ISO 8601, UTC)")


class OpenCellResponse(BaseModel):
    """Successful response of ``POST /api/cells/{cell_number}/open``.

    Also used for the ``503`` hardware-unavailable case, where the
    cell number is still known but ``success`` is ``False``.
    """

    success: bool = Field(..., description="True if the open command was dispatched")
    cell_number: int = Field(..., description="Cell number the command was issued for")
    message: str = Field(..., description="Human-readable status message (RU)")
    status: CellOpenStatus = Field(
        ...,
        description=(
            "Post-dispatch state of the cell. Only 'command_sent' / "
            "'dispatch_failed' are supported today because the hardware "
            "protocol does not return cell status. Do not interpret as "
            "physical open/closed confirmation."
        ),
    )


class OpenCellValidationErrorResponse(BaseModel):
    """Response body for the ``400`` validation error case.

    Used when the requested cell number is outside of the supported
    range. No cell number is echoed back because the input itself was
    invalid.
    """

    success: bool = Field(False, description="Always False for validation errors")
    message: str = Field(..., description="Human-readable error message (RU)")
