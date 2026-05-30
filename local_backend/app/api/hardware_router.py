"""Dev-only hardware simulation router.

Contains a single endpoint for development without a real controller:
``POST /api/hardware/mock/cells/{cell_number}/close``.
In production (use_mock_hardware=False) it returns 409.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.courier_schemas import ErrorResponse, MockCloseResponse
from app.services.hardware_mock_service import (
    CellNumberOutOfRangeError,
    HardwareMockService,
    MockNotAvailableError,
    get_hardware_mock_service,
)

router = APIRouter(prefix="/hardware", tags=["hardware-mock"])


@router.post(
    "/mock/cells/{cell_number}/close",
    response_model=MockCloseResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
    summary="[DEV] Имитировать закрытие ячейки (mock-режим)",
)
def mock_close_cell(
    cell_number: int,
    service: HardwareMockService = Depends(get_hardware_mock_service),
) -> MockCloseResponse:
    """Simulate the physical closing of a lock for development."""
    try:
        lock_status = service.close_cell(cell_number)
    except CellNumberOutOfRangeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except MockNotAvailableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))

    return MockCloseResponse(
        cell_number=cell_number,
        lock_status=lock_status,
        message=f"Ячейка №{cell_number} помечена как закрытая (mock).",
    )
