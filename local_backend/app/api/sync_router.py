"""Cloud synchronization router (debug/manual trigger).

Exposes a single endpoint to push pending events to the cloud on demand.
Useful while developing/operating the terminal before automatic background
sync is introduced.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.sync_service import SyncService, get_sync_service

router = APIRouter()


class PushPendingResponse(BaseModel):
    enabled: bool
    sent: int
    failed: int
    kept_pending: int
    message: str


@router.post("/sync/push-pending", response_model=PushPendingResponse)
def push_pending(
    service: SyncService = Depends(get_sync_service),
) -> PushPendingResponse:
    """Manually push pending events to the cloud."""
    summary = service.push_pending()
    return PushPendingResponse(**summary)
