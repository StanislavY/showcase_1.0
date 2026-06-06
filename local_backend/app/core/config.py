"""Application configuration.

A single, immutable ``AppConfig`` instance is exposed as ``config``.
Keep this module dependency-free: it is imported by both API and
service layers.
"""

import os
from pathlib import Path

from pydantic import BaseModel, Field

_LOCAL_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class AppConfig(BaseModel):
    service_name: str = "local_backend"
    api_prefix: str = "/api"

    # Path to the local postamat SQLite database.
    db_path: str = str(_LOCAL_BACKEND_DIR / "data" / "postamat.db")

    # Hardware integration toggle.
    # True  -> backend uses MockHardwareClient (safe for dev / no USB device).
    # False -> backend uses real HardwareClient backed by postamat_device.
    use_mock_hardware: bool = True

    # Courier authentication.
    #
    # The courier password is never stored on the device: only its PBKDF2
    # hash (computed with ``courier_password_salt``) is kept here. The
    # default values below are for development only and correspond to the
    # test password "111". On a real device these MUST be overridden via
    # environment variables / a local .env file.
    courier_password_salt: str = "postamat-local-test-salt-v1"
    courier_password_hash: str = "lQ4lycgmvJk01Xe3saXtic1acOOqWIbMgZhH4Qbm0xk="

    # Secret used to sign courier session tokens (HMAC-SHA256).
    courier_session_secret: str = "change-me-on-device"

    # Lifetime of an issued courier session token, in minutes.
    courier_session_ttl_minutes: int = 480

    # Administrator (control panel) authentication.
    #
    # Same approach as the courier password: the admin password is never
    # stored on the device, only its PBKDF2-HMAC-SHA256 hash (computed with
    # ``admin_password_salt`` and 200000 iterations). The defaults below are
    # for development only and correspond to the test password "111". On a
    # real device these MUST be overridden via environment / a local .env.
    admin_password_salt: str = "postamat-local-test-salt-v1"
    admin_password_hash: str = "lQ4lycgmvJk01Xe3saXtic1acOOqWIbMgZhH4Qbm0xk="

    # Secret used to sign admin session tokens (HMAC-SHA256).
    admin_session_secret: str = "change-me-admin-on-device"

    # Lifetime of an issued admin session token, in minutes.
    admin_session_ttl_minutes: int = 480

    # ------------------------------------------------------------------
    # Cloud (Django API v2) integration.
    #
    # The local backend acts as an Edge Agent that forwards events to the
    # central platform. All values below have safe dev defaults; on a real
    # device they MUST be provided via environment variables.
    #
    # cloud_sync_enabled defaults to False so a fresh dev install never
    # tries to reach the cloud until it is explicitly configured.
    # ------------------------------------------------------------------
    cloud_api_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "CLOUD_API_BASE_URL", "http://127.0.0.1:8001/api/v2"
        )
    )
    terminal_id: str = Field(
        default_factory=lambda: os.getenv("TERMINAL_ID", "dev-terminal")
    )
    terminal_token: str = Field(
        default_factory=lambda: os.getenv("TERMINAL_TOKEN", "")
    )
    cloud_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("CLOUD_TIMEOUT_SECONDS", 5.0)
    )
    cloud_sync_enabled: bool = Field(
        default_factory=lambda: _env_bool("CLOUD_SYNC_ENABLED", False)
    )


config = AppConfig()

USE_MOCK_HARDWARE: bool = config.use_mock_hardware
