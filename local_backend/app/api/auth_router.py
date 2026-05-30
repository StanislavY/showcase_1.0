"""Router for courier authentication.

A thin layer over :mod:`app.core.security`. It verifies the courier
password against the stored PBKDF2 hash and issues / validates signed
session tokens. No password is ever stored in plain text.

Note: this stage only adds login/check. Protecting the existing courier
endpoints with these tokens is a separate, later step.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import config
from app.core.security import (
    create_courier_session_token,
    verify_courier_session_token,
    verify_password,
)
from app.schemas.auth_schemas import (
    CourierCheckResponse,
    CourierLoginRequest,
    CourierLoginResponse,
)

router = APIRouter(prefix="/courier/auth", tags=["courier-auth"])

# Single-courier device for now; a real courier directory comes later.
_COURIER_ID = "courier-001"


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Return the token from an ``Authorization: Bearer <token>`` header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


@router.post(
    "/login",
    response_model=CourierLoginResponse,
    summary="Вход в режим курьера по паролю",
)
def courier_login(request: CourierLoginRequest) -> CourierLoginResponse:
    is_valid = verify_password(
        request.password,
        config.courier_password_salt,
        config.courier_password_hash,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CourierLoginResponse(
                success=False,
                token=None,
                courier_id=None,
                message="Неверный пароль курьера",
            ).model_dump(),
        )

    token = create_courier_session_token(_COURIER_ID)
    return CourierLoginResponse(
        success=True,
        token=token,
        courier_id=_COURIER_ID,
        message="Вход в режим курьера выполнен",
    )


@router.get(
    "/check",
    response_model=CourierCheckResponse,
    summary="Проверка активной сессии курьера",
)
def courier_check(
    authorization: str | None = Header(default=None),
) -> CourierCheckResponse:
    token = _extract_bearer_token(authorization)
    if not token or not verify_courier_session_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия недействительна или истекла",
        )

    return CourierCheckResponse(
        success=True,
        courier_id=_COURIER_ID,
        message="Сессия активна",
    )
