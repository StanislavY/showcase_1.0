"""Cell service: business logic for cell operations.

The service is the single owner of cell-related business rules:

* what cell numbers are valid for this postamat (1..27);
* whether the hardware is in a state where a command can be sent;
* how the result of a hardware call maps to a domain outcome.

It depends only on the hardware abstraction (``HardwareClient`` /
``MockHardwareClient``) and knows nothing about HTTP / FastAPI.
That keeps it easy to unit-test and reuse from other entry points
(WebSocket, CLI, scheduled tasks).
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.hardware.hardware_client import get_hardware_client

logger = logging.getLogger(__name__)


class _HardwarePort(Protocol):
    """Structural type the service relies on.

    Both ``HardwareClient`` and ``MockHardwareClient`` satisfy it.
    Declaring it explicitly documents the small contract the service
    actually needs and decouples it from concrete classes.
    """

    def is_available(self) -> bool: ...
    def open_cell(self, cell_number: int) -> bool: ...


class CellNumberOutOfRangeError(ValueError):
    """Raised when a requested cell number is outside the allowed range."""


class HardwareUnavailableError(RuntimeError):
    """Raised when the cell controller cannot accept commands right now."""


class CellService:
    """Business logic around opening postamat cells."""

    # Postamat layout: cells are numbered 1..27 inclusive.
    MIN_CELL_NUMBER: int = 1
    MAX_CELL_NUMBER: int = 27

    def __init__(self, hardware: _HardwarePort) -> None:
        self._hardware = hardware

    def open_cell(self, cell_number: int) -> None:
        """Validate the cell number and send the open command.

        Returns ``None`` on success. On failure raises a domain
        exception that the API layer translates into an HTTP status:

        * :class:`CellNumberOutOfRangeError` -> ``400``
        * :class:`HardwareUnavailableError`  -> ``503``
        """
        self._ensure_cell_number_in_range(cell_number)

        if not self._hardware.is_available():
            logger.warning(
                "open_cell(%s) refused: hardware reports unavailable",
                cell_number,
            )
            raise HardwareUnavailableError("Контроллер ячеек недоступен")

        # ``open_cell`` returns False on any dispatch error in the
        # legacy layer. From the caller's perspective this is also
        # "hardware unavailable" — we couldn't deliver the command.
        dispatched = self._hardware.open_cell(cell_number)
        if not dispatched:
            logger.error(
                "open_cell(%s) failed: hardware did not accept the command",
                cell_number,
            )
            raise HardwareUnavailableError("Контроллер ячеек недоступен")

        # TODO: Здесь нужно подключить реальное чтение статуса ячейки от
        # контроллера. На текущем протоколе Arduino (см.
        # postamat_device/libs/serial_ports_mng.py: Arduino.open_cell)
        # backend только пишет байты в порт и НЕ читает подтверждение,
        # поэтому факта физического открытия ячейки у нас нет. Когда
        # появится ответная часть протокола, тут должна быть проверка
        # через self._hardware (например, ожидание сигнала "opened" в
        # течение N секунд) с возвратом доменного статуса наверх.

    def _ensure_cell_number_in_range(self, cell_number: int) -> None:
        """Guard: cell number must be within the postamat layout."""
        if not (self.MIN_CELL_NUMBER <= cell_number <= self.MAX_CELL_NUMBER):
            raise CellNumberOutOfRangeError(
                f"Номер ячейки должен быть от "
                f"{self.MIN_CELL_NUMBER} до {self.MAX_CELL_NUMBER}"
            )


def get_cell_service() -> CellService:
    """Factory used as a FastAPI dependency.

    Creates a fresh service bound to the currently configured hardware
    client (real or mock, based on ``config.use_mock_hardware``).
    """
    return CellService(hardware=get_hardware_client())
