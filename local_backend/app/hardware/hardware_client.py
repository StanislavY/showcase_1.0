"""Hardware client: thin adapter over the existing postamat_device layer.

This module is the ONLY place in ``local_backend`` that is allowed to
talk to the legacy hardware project under ``postamat_device/``.
The rest of the application depends only on the public interface
defined here (``HardwareClient`` / ``MockHardwareClient``).

Integration notes
-----------------
The legacy module ``postamat_device/libs/serial_ports_mng.py`` performs
heavy side effects at import time:

* it instantiates ``_ARDUINO = Arduino()`` on module load, which reads
  ``libs.settings.data['arduino_vid_pid']`` and tries to open a serial
  port;
* it instantiates ``SCANNER = Scanner(callback=process_request)`` on
  module load as well;
* it imports ``main``, ``libs.settings``, ``libs.Globals`` using
  ``postamat_device/`` as the working directory.

Because of this, a plain ``import`` from ``local_backend`` can fail or
trigger USB / settings access. We therefore:

1. Never import the legacy module at top level — only lazily, inside a
   guarded helper.
2. Wrap every call to the legacy layer in ``try/except`` so that a
   broken USB controller or a missing settings file does NOT crash the
   backend.
3. If the legacy import is impossible in the current environment,
   ``HardwareClient`` transparently degrades to a logging-only stub
   (mock-like behavior) instead of raising.
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.cell_status import LockStatus

logger = logging.getLogger(__name__)


def map_hardware_lock_status(raw: Any) -> LockStatus:
    """Map a hardware lock status to the domain ``LockStatus``.

    A careful adapter: the controller may send different formats
    (strings, numbers, boolean codes). Here we do NOT break the existing
    protocol, we only normalize whatever arrived. Unknown values become
    ``UNKNOWN`` so the business logic does not crash.
    """
    if raw is None:
        return LockStatus.UNKNOWN
    if isinstance(raw, LockStatus):
        return raw
    text = str(raw).strip().upper()
    open_codes = {"OPEN", "OPENED", "1", "TRUE", "O"}
    closed_codes = {"CLOSED", "CLOSE", "0", "FALSE", "C"}
    error_codes = {"ERROR", "ERR", "FAULT", "-1", "E"}
    if text in open_codes:
        return LockStatus.OPEN
    if text in closed_codes:
        return LockStatus.CLOSED
    if text in error_codes:
        return LockStatus.ERROR
    return LockStatus.UNKNOWN


def _load_legacy_module() -> Any | None:
    """Try to import ``postamat_device.libs.serial_ports_mng`` lazily.

    Returns the imported module on success, ``None`` on any failure.
    Never raises — the caller decides how to degrade.
    """
    try:
        # Imported lazily on purpose: top-level side effects of the
        # legacy module (serial port probing, settings loading) must
        # NOT run when ``local_backend`` is imported.
        from postamat_device.libs import serial_ports_mng  # type: ignore

        return serial_ports_mng
    except Exception as exc:  # noqa: BLE001 - we really want to swallow everything here
        logger.warning(
            "Legacy hardware module is unavailable, HardwareClient will "
            "operate in degraded (no-op) mode. Reason: %s",
            exc,
        )
        return None


class HardwareClient:
    """Adapter over the real Arduino-backed cell controller.

    Public surface is intentionally small so the rest of the app stays
    decoupled from ``pyserial`` and from ``postamat_device``.

    Status reading
    --------------
    The current legacy protocol (see ``Arduino.open_cell`` in
    ``postamat_device/libs/serial_ports_mng.py``) is write-only: the
    backend sends a cell number and never reads back whether the cell
    physically opened. As a result this client deliberately does NOT
    expose a ``get_cell_status`` method or a polling thread — adding
    one would require fabricating commands the real controller does
    not support.

    TODO: Wire up real cell-status reading from the controller here, as
    soon as we agree on the response side of the Arduino protocol
    (message format, per-cell identifier, timings).
    """

    def __init__(self) -> None:
        self._module = _load_legacy_module()

    @property
    def _arduino(self) -> Any | None:
        if self._module is None:
            return None
        return getattr(self._module, "_ARDUINO", None)

    def is_available(self) -> bool:
        """Return True if the underlying hardware reports a live connection."""
        arduino = self._arduino
        if arduino is None:
            return False
        try:
            return bool(arduino.is_connected())
        except Exception as exc:  # noqa: BLE001
            logger.exception("HardwareClient.is_available failed: %s", exc)
            return False

    def open_cell(self, cell_number: int) -> bool:
        """Send an open-cell command to the hardware layer.

        Returns True if the command was dispatched successfully,
        False on any error. We do NOT verify the physical state of
        the cell — only the fact that the command left the backend.

        TODO: Wire up real cell-status reading from the controller here.
        Currently, in the legacy layer
        ``postamat_device/libs/serial_ports_mng.py`` the method
        ``Arduino.open_cell`` only does ``write(...)`` to the serial port
        and does not read a response. Once the controller starts
        reporting state ("opened" / "closed" / "error"), this part of the
        protocol should be read here and the method should return a
        domain status instead of a bool — or expose a separate
        ``get_cell_status`` method. This must not be done before the
        hardware response format is confirmed.
        """
        arduino = self._arduino
        if arduino is None:
            logger.warning(
                "open_cell(%s) ignored: hardware layer is not loaded",
                cell_number,
            )
            return False
        try:
            if not arduino.is_connected():
                logger.warning(
                    "open_cell(%s) ignored: Arduino is not connected",
                    cell_number,
                )
                return False
            arduino.open_cell(str(cell_number))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "open_cell(%s) failed in legacy hardware layer: %s",
                cell_number,
                exc,
            )
            return False

    def open_cells(self, cell_numbers: list[int]) -> dict:
        """Open several cells sequentially.

        Returns a dict::

            {
                "results": {cell_number: bool, ...},
                "ok": bool,        # True iff every cell succeeded
                "total": int,
                "succeeded": int,
            }
        """
        results: dict[int, bool] = {}
        for number in cell_numbers:
            results[number] = self.open_cell(number)
        succeeded = sum(1 for v in results.values() if v)
        return {
            "results": results,
            "ok": succeeded == len(cell_numbers) and len(cell_numbers) > 0,
            "total": len(cell_numbers),
            "succeeded": succeeded,
        }

    def get_lock_status(self, cell_number: int) -> LockStatus:
        """Return the domain lock status reported by the controller.

        TODO: Wire up real lock-status reading from the controller here.
        The current legacy protocol (``Arduino.open_cell`` in
        ``postamat_device``) is write-only and does not report the cell
        state, so the honest answer right now is ``UNKNOWN``. Once the
        controller starts sending a status, read it here and pass it
        through :func:`map_hardware_lock_status` without changing the
        method signature.
        """
        arduino = self._arduino
        if arduino is None:
            return LockStatus.UNKNOWN
        getter = getattr(arduino, "get_lock_status", None)
        if getter is None:
            # The controller cannot report a status yet — do not make one up.
            return LockStatus.UNKNOWN
        try:
            return map_hardware_lock_status(getter(str(cell_number)))
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "get_lock_status(%s) failed in legacy layer: %s",
                cell_number,
                exc,
            )
            return LockStatus.ERROR


class MockHardwareClient:
    """Drop-in replacement for ``HardwareClient`` without real hardware.

    Useful for development, tests, and CI where no USB controller is
    attached. Unlike the real client it keeps an in-memory model of each
    cell's lock so the courier workflow can be exercised end-to-end:

    * ``open_cell`` moves the lock to ``OPEN``;
    * ``get_lock_status`` returns the current simulated state;
    * ``simulate_close`` simulates a physical closing (``CLOSED``).

    The state must live across HTTP requests, so the application uses a
    single (singleton) instance — see :func:`get_hardware_client`.
    """

    def __init__(self) -> None:
        self.opened_cells: list[int] = []
        self._lock_status: dict[int, LockStatus] = {}

    def is_available(self) -> bool:
        return True

    def open_cell(self, cell_number: int) -> bool:
        logger.info("[MockHardwareClient] open_cell(%s)", cell_number)
        self.opened_cells.append(cell_number)
        self._lock_status[cell_number] = LockStatus.OPEN
        return True

    def open_cells(self, cell_numbers: list[int]) -> dict:
        results = {number: self.open_cell(number) for number in cell_numbers}
        succeeded = sum(1 for v in results.values() if v)
        return {
            "results": results,
            "ok": succeeded == len(cell_numbers) and len(cell_numbers) > 0,
            "total": len(cell_numbers),
            "succeeded": succeeded,
        }

    def get_lock_status(self, cell_number: int) -> LockStatus:
        """Return the simulated lock status (defaults to ``UNKNOWN``)."""
        return self._lock_status.get(cell_number, LockStatus.UNKNOWN)

    def simulate_close(self, cell_number: int) -> LockStatus:
        """Simulate a physical cell closing (dev/mock only)."""
        logger.info("[MockHardwareClient] simulate_close(%s)", cell_number)
        self._lock_status[cell_number] = LockStatus.CLOSED
        return LockStatus.CLOSED


# A single client instance per process. This is critical for mock mode:
# the lock state model must persist across requests.
_client_singleton: HardwareClient | MockHardwareClient | None = None


def get_hardware_client() -> HardwareClient | MockHardwareClient:
    """Factory: pick a client based on ``config.use_mock_hardware``.

    Returns the same instance for the whole process lifetime so that
    internal state (e.g. the mock's simulated locks) is not reset on
    every request.
    """
    # Imported here to avoid a circular import with ``app.core.config``
    # if config ever grows to import hardware metadata.
    from app.core.config import config

    global _client_singleton
    if _client_singleton is None:
        _client_singleton = (
            MockHardwareClient()
            if config.use_mock_hardware
            else HardwareClient()
        )
    return _client_singleton
