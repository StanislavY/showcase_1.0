"""Application configuration.

A single, immutable ``AppConfig`` instance is exposed as ``config``.
Keep this module dependency-free: it is imported by both API and
service layers.
"""

from pydantic import BaseModel


class AppConfig(BaseModel):
    service_name: str = "local_backend"
    api_prefix: str = "/api"

    # Hardware integration toggle.
    # True  -> backend uses MockHardwareClient (safe for dev / no USB device).
    # False -> backend uses real HardwareClient backed by postamat_device.
    use_mock_hardware: bool = True


config = AppConfig()

USE_MOCK_HARDWARE: bool = config.use_mock_hardware
