"""Application configuration.

A single, immutable ``AppConfig`` instance is exposed as ``config``.
Keep this module dependency-free: it is imported by both API and
service layers.
"""

from pathlib import Path

from pydantic import BaseModel

_LOCAL_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


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


config = AppConfig()

USE_MOCK_HARDWARE: bool = config.use_mock_hardware
