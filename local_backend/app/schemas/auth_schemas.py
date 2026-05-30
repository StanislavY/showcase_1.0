"""Pydantic schemas for courier authentication.

They describe the request/response contracts of the courier login/check
endpoints in :mod:`app.api.auth_router`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CourierLoginRequest(BaseModel):
    """Courier login request: just the password to verify."""

    password: str = Field(..., description="Пароль курьера")


class CourierLoginResponse(BaseModel):
    """Result of a courier login attempt."""

    success: bool
    token: str | None = None
    courier_id: str | None = None
    message: str


class CourierCheckResponse(BaseModel):
    """Result of a courier session check."""

    success: bool
    courier_id: str | None = None
    message: str
