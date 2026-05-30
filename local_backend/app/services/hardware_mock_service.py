"""Dev-only hardware simulation service.

Used by the single endpoint
``POST /api/hardware/mock/cells/{cell_number}/close`` for development
without a real controller. In production (use_mock_hardware=False) the
close operation cannot be simulated and the service raises an error.

The router stays thin and does not touch hardware directly — it calls
this service, which encapsulates access to the hardware client.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.cell_status import LockStatus
from app.domain.layout import MAX_CELL_NUMBER, MIN_CELL_NUMBER
from app.hardware.hardware_client import get_hardware_client


class MockNotAvailableError(RuntimeError):
    """Simulation is unavailable: a real controller is connected."""


class CellNumberOutOfRangeError(ValueError):
    """Cell number is outside the 1..27 range."""


class _MockHardwarePort(Protocol):
    def simulate_close(self, cell_number: int) -> LockStatus: ...


class HardwareMockService:
    """Simulates physical lock events for development."""

    def __init__(self, hardware: object) -> None:
        self._hardware = hardware

    def close_cell(self, cell_number: int) -> LockStatus:
        if not (MIN_CELL_NUMBER <= cell_number <= MAX_CELL_NUMBER):
            raise CellNumberOutOfRangeError(
                f"Номер ячейки должен быть от {MIN_CELL_NUMBER} "
                f"до {MAX_CELL_NUMBER}."
            )
        simulate = getattr(self._hardware, "simulate_close", None)
        if simulate is None:
            raise MockNotAvailableError(
                "Имитация закрытия доступна только в mock-режиме "
                "(use_mock_hardware=True)."
            )
        return simulate(cell_number)


def get_hardware_mock_service() -> HardwareMockService:
    """Factory used as a FastAPI dependency."""
    return HardwareMockService(hardware=get_hardware_client())
