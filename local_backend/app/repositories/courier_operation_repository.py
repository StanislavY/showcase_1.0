"""Repository for courier operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.database import get_connection
from app.domain.courier_operation import CourierOperationStatus, CourierOperationType


@dataclass(frozen=True)
class CourierOperationRecord:
    """A row of the courier_operations table."""

    id: int
    operation_type: CourierOperationType
    status: CourierOperationStatus
    cell_number: int
    old_product_id: str | None
    old_product_name: str | None
    old_product_price: float | None
    new_product_id: str | None
    new_product_name: str | None
    new_product_price: float | None
    courier_id: str | None
    error_message: str | None
    started_at: str
    finished_at: str | None


class CourierOperationRepository:
    """Data access for courier operations."""

    def create(
        self,
        operation_type: CourierOperationType,
        cell_number: int,
        *,
        courier_id: str | None = None,
        new_product_id: str | None = None,
        new_product_name: str | None = None,
        new_product_price: float | None = None,
        old_product_id: str | None = None,
        old_product_name: str | None = None,
        old_product_price: float | None = None,
    ) -> int:
        """Create an operation in the CREATED status."""
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO courier_operations (
                    operation_type, status, cell_number,
                    old_product_id, old_product_name, old_product_price,
                    new_product_id, new_product_name, new_product_price,
                    courier_id, started_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation_type.value,
                    CourierOperationStatus.CREATED.value,
                    cell_number,
                    old_product_id,
                    old_product_name,
                    old_product_price,
                    new_product_id,
                    new_product_name,
                    new_product_price,
                    courier_id,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def get_by_id(self, operation_id: int) -> CourierOperationRecord | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM courier_operations WHERE id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_record(row)

    def update_status(
        self,
        operation_id: int,
        status: CourierOperationStatus,
        *,
        error_message: str | None = None,
        finished: bool = False,
    ) -> None:
        """Move the operation to a new status.

        ``finished=True`` sets ``finished_at`` (used for the terminal
        statuses COMPLETED / CANCELLED / FAILED).
        """
        finished_at = (
            datetime.now(UTC).replace(microsecond=0).isoformat()
            if finished
            else None
        )
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE courier_operations
                SET status = ?,
                    error_message = COALESCE(?, error_message),
                    finished_at = COALESCE(?, finished_at)
                WHERE id = ?
                """,
                (status.value, error_message, finished_at, operation_id),
            )

    def list_active(self) -> list[CourierOperationRecord]:
        """Operations that are not in a terminal status."""
        terminal = (
            CourierOperationStatus.COMPLETED.value,
            CourierOperationStatus.CANCELLED.value,
            CourierOperationStatus.FAILED.value,
        )
        placeholders = ", ".join("?" for _ in terminal)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM courier_operations
                WHERE status NOT IN ({placeholders})
                ORDER BY id
                """,
                terminal,
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def _row_to_record(row) -> CourierOperationRecord:
    return CourierOperationRecord(
        id=int(row["id"]),
        operation_type=CourierOperationType(row["operation_type"]),
        status=CourierOperationStatus(row["status"]),
        cell_number=int(row["cell_number"]),
        old_product_id=row["old_product_id"],
        old_product_name=row["old_product_name"],
        old_product_price=row["old_product_price"],
        new_product_id=row["new_product_id"],
        new_product_name=row["new_product_name"],
        new_product_price=row["new_product_price"],
        courier_id=row["courier_id"],
        error_message=row["error_message"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )
