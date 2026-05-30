"""Router for the sales workflow (limit + purchases).

The router is intentionally thin: it accepts the HTTP request, delegates
to :class:`SalesService`, and converts domain exceptions into HTTP
responses with the JSON shape agreed with the frontend. No business
rules live here.

Routes:

* ``GET  /api/sales/limit``                  — public, current limit
* ``POST /api/admin/sales/limit``            — admin only, set a new limit
* ``POST /api/sales/cells/{cell_number}/sell`` — public, buy from a cell
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.security import verify_admin_session_token
from app.schemas.sales_schemas import (
    SaleResponse,
    SalesLimitSummaryResponse,
    SetSalesLimitRequest,
)
from app.services.sales_service import (
    CellNotAvailableError,
    HardwareOpenError,
    LimitExceededError,
    NoProductError,
    ProductPriceError,
    SalesService,
    SalesValidationError,
    get_sales_service,
)

router = APIRouter(tags=["sales"])


def require_admin(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: validate the admin bearer token, return admin_id."""
    token: str | None = None
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    admin_id = verify_admin_session_token(token) if token else None
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация администратора",
        )
    return admin_id


@router.get(
    "/sales/limit",
    response_model=SalesLimitSummaryResponse,
    summary="Текущий лимит продаж",
)
def get_sales_limit(
    service: SalesService = Depends(get_sales_service),
) -> SalesLimitSummaryResponse:
    return service.get_current_limit_summary()


@router.post(
    "/admin/sales/limit",
    response_model=SalesLimitSummaryResponse,
    summary="Установить новый лимит продаж (администратор)",
)
def set_sales_limit(
    request: SetSalesLimitRequest,
    _admin_id: str = Depends(require_admin),
    service: SalesService = Depends(get_sales_service),
) -> SalesLimitSummaryResponse | JSONResponse:
    try:
        return service.set_new_limit(request.limit_amount_kopecks)
    except SalesValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc)},
        )


@router.post(
    "/sales/cells/{cell_number}/sell",
    response_model=SaleResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": SaleResponse},
        status.HTTP_409_CONFLICT: {"model": SaleResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": SaleResponse},
    },
    summary="Продажа товара из ячейки",
)
def sell_from_cell(
    cell_number: int,
    service: SalesService = Depends(get_sales_service),
) -> SaleResponse | JSONResponse:
    try:
        return service.sell_from_cell(cell_number)
    except SalesValidationError as exc:
        return _error(status.HTTP_400_BAD_REQUEST, str(exc))
    except NoProductError as exc:
        return _error(status.HTTP_409_CONFLICT, str(exc))
    except CellNotAvailableError as exc:
        return _error(status.HTTP_409_CONFLICT, str(exc))
    except (LimitExceededError, ProductPriceError) as exc:
        return _error(status.HTTP_409_CONFLICT, str(exc))
    except HardwareOpenError as exc:
        return _error(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message},
    )
