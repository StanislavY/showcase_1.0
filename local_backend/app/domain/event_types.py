"""Event log types (events.event_type).

A centralized list of string constants so that the service and tests
do not duplicate magic strings or diverge in spelling.
"""

from enum import StrEnum


class EventType(StrEnum):
    """Minimal set of event types for the courier workflow."""

    LOAD_STARTED = "LOAD_STARTED"
    UNLOAD_STARTED = "UNLOAD_STARTED"
    REPLACE_STARTED = "REPLACE_STARTED"
    CELL_OPEN_COMMAND_SENT = "CELL_OPEN_COMMAND_SENT"
    LOCK_STATUS_UPDATED = "LOCK_STATUS_UPDATED"
    CELL_OPENED = "CELL_OPENED"
    COURIER_ACTION_DONE = "COURIER_ACTION_DONE"
    CELL_CLOSED = "CELL_CLOSED"
    PRODUCT_LOADED = "PRODUCT_LOADED"
    PRODUCT_UNLOADED = "PRODUCT_UNLOADED"
    PRODUCT_REPLACED = "PRODUCT_REPLACED"
    OPERATION_CANCELLED = "OPERATION_CANCELLED"
    OPERATION_FAILED = "OPERATION_FAILED"
    CELL_ERROR = "CELL_ERROR"

    # Sales workflow (limit + purchases).
    SALES_LIMIT_SET = "SALES_LIMIT_SET"
    SALE_STARTED = "SALE_STARTED"
    SALE_COMPLETED = "SALE_COMPLETED"
    SALE_FAILED = "SALE_FAILED"

    # Online-sales pickup workflow (cloud-driven issuance).
    #
    # These values intentionally match the cloud API v2 TerminalEvent choices
    # (OPEN_CONFIRMED / ISSUE_COMPLETED / ISSUE_FAILED) so an event can be
    # forwarded to ``POST /api/v2/terminal/issue-events/`` without remapping.
    ISSUE_COMPLETED = "ISSUE_COMPLETED"
    ISSUE_FAILED = "ISSUE_FAILED"
