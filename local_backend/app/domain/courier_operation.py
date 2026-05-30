"""Courier operation types and statuses (domain model)."""

from enum import StrEnum


class CourierOperationType(StrEnum):
    """Kind of courier operation on a cell."""

    LOAD = "LOAD"  # load a product
    UNLOAD = "UNLOAD"  # unload a product
    REPLACE = "REPLACE"  # replace a product


class CourierOperationStatus(StrEnum):
    """Lifecycle of a courier operation.

    The extended workflow is tied to the lock status: an operation cannot
    be completed until the controller confirms the cell is closed.
    """

    CREATED = "CREATED"
    CELL_OPEN_COMMAND_SENT = "CELL_OPEN_COMMAND_SENT"
    # Open command sent; waiting for the controller to confirm opening.
    WAITING_CELL_OPEN = "WAITING_CELL_OPEN"
    # Lock is open; the courier must place/take/replace the product.
    WAITING_COURIER_ACTION = "WAITING_COURIER_ACTION"
    # Courier pressed "I performed the action"; waiting for the lock to close.
    WAITING_CELL_CLOSE = "WAITING_CELL_CLOSE"
    # Controller reported the lock is closed; the operation can be completed.
    READY_TO_CONFIRM = "READY_TO_CONFIRM"
    # Kept for backward compatibility with previously created operations.
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


# Statuses in which an operation is considered finished and immutable.
TERMINAL_OPERATION_STATUSES = frozenset(
    {
        CourierOperationStatus.COMPLETED,
        CourierOperationStatus.CANCELLED,
        CourierOperationStatus.FAILED,
    }
)
