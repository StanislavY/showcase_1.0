"""Domain statuses for the sales workflow (limits and purchases)."""

from enum import StrEnum


class SalesLimitStatus(StrEnum):
    """Lifecycle of a sales limit.

    Only one ``ACTIVE`` limit may exist at a time; setting a new limit
    closes the previous one (``CLOSED``).
    """

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class SaleStatus(StrEnum):
    """Lifecycle of a single sale (purchase from a cell)."""

    OPENING = "OPENING"  # cell open command in progress
    COMPLETED = "COMPLETED"  # cell opened, sale counted
    FAILED = "FAILED"  # hardware failed, sale not counted
