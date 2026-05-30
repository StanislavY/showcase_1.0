"""Pydantic schemas for administrator (control panel) authentication.

They describe the request/response contracts of the admin login/check
endpoints in :mod:`app.api.admin_auth_router`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    """Admin login request: just the password to verify."""

    password: str = Field(..., description="Пароль администратора")


class AdminLoginResponse(BaseModel):
    """Result of an admin login attempt."""

    success: bool
    token: str | None = None
    admin_id: str | None = None
    message: str


class AdminCheckResponse(BaseModel):
    """Result of an admin session check."""

    success: bool
    admin_id: str | None = None
    message: str
