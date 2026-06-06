"""Router for the online-sales pickup workflow ("Забрать товар").

The router is intentionally thin: it accepts the HTTP request, delegates to
:class:`OnlineSalesService`, and returns the service's structured result as
JSON. No business rules live here.

Every outcome (in-progress, cloud offline, no products, completed, failed) is
encoded in the JSON body via ``success`` / ``code`` / ``message`` /
``next_action``, so the response is always HTTP 200 and the frontend decides
what to show based on the body.

Route:

* ``POST /api/online-sales/pickup`` — public, open the customer's cells.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.online_sales_service import (
    OnlineSalesService,
    get_online_sales_service,
)

router = APIRouter(tags=["online-sales"])


@router.post(
    "/online-sales/pickup",
    summary='Забрать товар (онлайн-продажи)',
)
def pickup(
    service: OnlineSalesService = Depends(get_online_sales_service),
) -> dict:
    """Run the online-sales pickup scenario and return its structured result."""
    return service.pickup()
