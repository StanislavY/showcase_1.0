"""Router for courier service operations.

A thin layer: it accepts the HTTP request, delegates to
:class:`CourierOperationService` and turns domain exceptions into
clear HTTP responses. No business rules or DB/hardware access live here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.courier_schemas import (
    ConfirmResponse,
    CourierOperationView,
    ErrorResponse,
    LoadStartRequest,
    OperationStatusResponse,
    OperationStepResponse,
    ReplaceStartRequest,
    UnloadStartRequest,
)
from app.services.courier_operation_service import (
    BusinessRuleError,
    CourierOperationService,
    HardwareUnavailableError,
    OperationConflictError,
    OperationNotFoundError,
    get_courier_operation_service,
)

router = APIRouter(prefix="/courier", tags=["courier"])

_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
}


def _raise_http(exc: Exception) -> None:
    """Map a domain exception to an HTTPException with a RU message."""
    if isinstance(exc, OperationNotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, OperationConflictError):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, HardwareUnavailableError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    if isinstance(exc, BusinessRuleError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise exc


@router.post(
    "/operations/load/start",
    response_model=OperationStepResponse,
    responses=_ERROR_RESPONSES,
    summary="Начать загрузку товара в пустую ячейку",
)
def start_load(
    request: LoadStartRequest,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> OperationStepResponse:
    try:
        return service.start_load(request)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.post(
    "/operations/unload/start",
    response_model=OperationStepResponse,
    responses=_ERROR_RESPONSES,
    summary="Начать выгрузку товара из ячейки",
)
def start_unload(
    request: UnloadStartRequest,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> OperationStepResponse:
    try:
        return service.start_unload(request)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.post(
    "/operations/replace/start",
    response_model=OperationStepResponse,
    responses=_ERROR_RESPONSES,
    summary="Начать замену товара в ячейке",
)
def start_replace(
    request: ReplaceStartRequest,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> OperationStepResponse:
    try:
        return service.start_replace(request)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/refresh-lock-status",
    response_model=OperationStepResponse,
    responses=_ERROR_RESPONSES,
    summary="Обновить статус замка и продвинуть операцию",
)
def refresh_lock_status(
    operation_id: int,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> OperationStepResponse:
    try:
        return service.refresh_lock_status(operation_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/courier-action-done",
    response_model=OperationStepResponse,
    responses=_ERROR_RESPONSES,
    summary="Курьер выполнил действие с товаром",
)
def courier_action_done(
    operation_id: int,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> OperationStepResponse:
    try:
        return service.courier_action_done(operation_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/confirm",
    response_model=ConfirmResponse,
    responses=_ERROR_RESPONSES,
    summary="Завершить операцию после закрытия ячейки",
)
def confirm_operation(
    operation_id: int,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> ConfirmResponse:
    try:
        return service.confirm(operation_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/cancel",
    response_model=OperationStepResponse,
    responses=_ERROR_RESPONSES,
    summary="Отменить операцию",
)
def cancel_operation(
    operation_id: int,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> OperationStepResponse:
    try:
        return service.cancel(operation_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.get(
    "/operations/active",
    response_model=list[CourierOperationView],
    summary="Активные (незавершённые) операции",
)
def list_active(
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> list[CourierOperationView]:
    return service.list_active()


@router.get(
    "/operations/{operation_id}/status",
    response_model=OperationStatusResponse,
    responses=_ERROR_RESPONSES,
    summary="Удобный DTO статуса операции для frontend",
)
def operation_status(
    operation_id: int,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> OperationStatusResponse:
    try:
        return service.get_status(operation_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)


@router.get(
    "/operations/{operation_id}",
    response_model=CourierOperationView,
    responses=_ERROR_RESPONSES,
    summary="Состояние операции",
)
def get_operation(
    operation_id: int,
    service: CourierOperationService = Depends(get_courier_operation_service),
) -> CourierOperationView:
    try:
        return service.get_operation(operation_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http(exc)
