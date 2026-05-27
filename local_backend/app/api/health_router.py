"""Health-check router.

Exposes a single endpoint used by deployment scripts and the local
frontend to verify that the backend process is alive.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import config


class HealthResponse(BaseModel):
    status: str
    service: str


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=config.service_name)
