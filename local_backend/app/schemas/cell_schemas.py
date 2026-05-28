"""Pydantic schemas for cell-related API contracts.

Schemas describe the shape of JSON returned by ``/api/cells`` endpoints.
They intentionally mirror the contract documented in the project spec
so the frontend can rely on a stable structure for both success and
error cases.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Possible values of ``OpenCellResponse.status``.
#
# IMPORTANT: today the cell controller protocol used by this project is
# write-only — the backend sends an "open" command and never reads back
# whether the cell physically opened. Therefore we deliberately do NOT
# expose ``"open"`` / ``"closed"`` here: it would imply confirmation we
# cannot give. The only honest post-dispatch state is ``"command_sent"``.
#
# TODO: Здесь нужно подключить реальное чтение статуса ячейки от
# контроллера. Когда протокол получит ответную часть, расширить этот
# Literal значениями вроде "open" / "closed" / "timeout" и пробрасывать
# их из CellService.
CellOpenStatus = Literal["command_sent", "dispatch_failed"]


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
