"""Router for administrator (control panel) authentication.

A thin layer over :mod:`app.core.security`. It verifies the admin password
against the stored PBKDF2 hash and issues / validates signed session
tokens. No password is ever stored in plain text on the device.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import config
from app.core.security import (
    create_admin_session_token,
    verify_admin_session_token,
    verify_password,
)
from app.schemas.admin_auth_schemas import (
    AdminCheckResponse,
    AdminLoginRequest,
    AdminLoginResponse,
)

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

# Single-admin device for now; a real admin directory comes later.
_ADMIN_ID = "admin-001"


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
    response_model=AdminLoginResponse,
    summary="Вход в панель управления по паролю",
)
def admin_login(request: AdminLoginRequest) -> AdminLoginResponse:
    is_valid = verify_password(
        request.password,
        config.admin_password_salt,
        config.admin_password_hash,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AdminLoginResponse(
                success=False,
                token=None,
                admin_id=None,
                message="Неверный пароль администратора",
            ).model_dump(),
        )

    token = create_admin_session_token(_ADMIN_ID)
    return AdminLoginResponse(
        success=True,
        token=token,
        admin_id=_ADMIN_ID,
        message="Вход в панель управления выполнен",
    )


@router.get(
    "/check",
    response_model=AdminCheckResponse,
    summary="Проверка активной сессии администратора",
)
def admin_check(
    authorization: str | None = Header(default=None),
) -> AdminCheckResponse:
    token = _extract_bearer_token(authorization)
    admin_id = verify_admin_session_token(token) if token else None
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия администратора недействительна или истекла",
        )

    return AdminCheckResponse(
        success=True,
        admin_id=admin_id,
        message="Сессия администратора активна",
    )
