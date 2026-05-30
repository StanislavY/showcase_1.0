"""Router for cell-related endpoints.

The router is intentionally thin: it accepts the HTTP request,
delegates to :class:`CellService`, and converts domain exceptions
into HTTP responses with the JSON shape agreed with the frontend.
No business rules (cell number ranges, hardware health) live here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.schemas.cell_schemas import (
    CellResponse,
    OpenCellResponse,
    OpenCellValidationErrorResponse,
)
from app.services.cell_service import (
    CellNumberOutOfRangeError,
    CellService,
    HardwareUnavailableError,
    get_cell_service,
)

router = APIRouter(prefix="/cells", tags=["cells"])


@router.get(
    "",
    response_model=list[CellResponse],
    summary="Список всех ячеек постамата",
)
def list_cells_endpoint(
    service: CellService = Depends(get_cell_service),
) -> list[CellResponse]:
    """Return the 27 cells with their bookkeeping state from SQLite."""
    return service.list_cells()


@router.post(
    "/{cell_number}/open",
    response_model=OpenCellResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": OpenCellValidationErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": OpenCellResponse},
    },
    summary="Открыть одну ячейку постамата",
)
def open_cell_endpoint(
    cell_number: int,
    service: CellService = Depends(get_cell_service),
) -> OpenCellResponse | JSONResponse:
    """Open a single cell by its number.

    Flow:

    1. ``cell_number`` is parsed from the path (FastAPI ensures it is an int).
    2. The actual validation (range 1..27) and hardware dispatch live in
       :class:`CellService`.
    3. Domain exceptions are mapped to the JSON contract expected by the
       frontend — ``JSONResponse`` is used directly so the error body
       matches the spec exactly (no extra ``detail`` wrapper).
    """
    try:
        service.open_cell(cell_number)
    except CellNumberOutOfRangeError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=OpenCellValidationErrorResponse(
                success=False,
                message=str(exc),
            ).model_dump(),
        )
    except HardwareUnavailableError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=OpenCellResponse(
                success=False,
                cell_number=cell_number,
                message=str(exc),
                status="dispatch_failed",
            ).model_dump(),
        )

    return OpenCellResponse(
        success=True,
        cell_number=cell_number,
        message=f"Команда на открытие ячейки №{cell_number} отправлена",
        status="command_sent",
    )
