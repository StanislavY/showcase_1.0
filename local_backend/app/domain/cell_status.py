"""Postamat cell statuses (domain model)."""

from enum import StrEnum


class CellStatus(StrEnum):
    """State of a cell in the postamat bookkeeping."""

    EMPTY = "EMPTY"  # cell is empty
    LOADED = "LOADED"  # cell holds a product
    SERVICE = "SERVICE"  # a courier is working with the cell
    BLOCKED = "BLOCKED"  # cell is blocked
    ERROR = "ERROR"  # cell is in error


class LockStatus(StrEnum):
    """Domain status of a cell lock.

    The hardware controller may send arbitrary codes/strings — they
    should be mapped to these values (see ``hardware_client``) without
    breaking the existing protocol format.
    """

    UNKNOWN = "UNKNOWN"  # lock status is unknown
    OPEN = "OPEN"  # lock/cell is open
    CLOSED = "CLOSED"  # lock/cell is closed
    ERROR = "ERROR"  # lock error
