"""Cell repository: reading and updating records in SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.database import get_connection
from app.domain.cell_status import CellStatus, LockStatus

_CELL_COLUMNS = """
    number, status, product_id, product_name, product_price,
    current_operation_id, lock_status, last_lock_event_at, updated_at
"""


@dataclass(frozen=True)
class CellRecord:
    """A row of the cells table."""

    number: int
    status: CellStatus
    product_id: str | None
    product_name: str | None
    product_price: float | None
    current_operation_id: int | None
    lock_status: LockStatus
    last_lock_event_at: str | None
    updated_at: str


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class CellRepository:
    """Data access for postamat cells."""

    def list_all(self) -> list[CellRecord]:
        """All cells, ordered by number."""
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT {_CELL_COLUMNS} FROM cells ORDER BY number"
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def get_by_number(self, number: int) -> CellRecord | None:
        """A single cell by number, or ``None``."""
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT {_CELL_COLUMNS} FROM cells WHERE number = ?",
                (number,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_record(row)

    def count(self) -> int:
        with get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM cells").fetchone()
        return int(row["cnt"])

    def update_status(
        self,
        number: int,
        status: CellStatus,
        *,
        product_id: str | None = None,
        product_name: str | None = None,
        product_price: float | None = None,
        current_operation_id: int | None = None,
        clear_product: bool = False,
    ) -> None:
        """Update the cell status and (optionally) its product."""
        now = _utc_now_iso()
        with get_connection() as conn:
            if clear_product:
                conn.execute(
                    """
                    UPDATE cells
                    SET status = ?, product_id = NULL, product_name = NULL,
                        product_price = NULL, current_operation_id = ?,
                        updated_at = ?
                    WHERE number = ?
                    """,
                    (status.value, current_operation_id, now, number),
                )
            else:
                conn.execute(
                    """
                    UPDATE cells
                    SET status = ?, product_id = ?, product_name = ?,
                        product_price = ?, current_operation_id = ?,
                        updated_at = ?
                    WHERE number = ?
                    """,
                    (
                        status.value,
                        product_id,
                        product_name,
                        product_price,
                        current_operation_id,
                        now,
                        number,
                    ),
                )

    def update_lock_status(self, number: int, lock_status: LockStatus) -> str:
        """Update the lock status and the time of the last lock event.

        Returns the recorded ``last_lock_event_at`` (ISO 8601, UTC).
        """
        now = _utc_now_iso()
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE cells
                SET lock_status = ?, last_lock_event_at = ?, updated_at = ?
                WHERE number = ?
                """,
                (lock_status.value, now, now, number),
            )
        return now


def _row_to_record(row) -> CellRecord:
    return CellRecord(
        number=int(row["number"]),
        status=CellStatus(row["status"]),
        product_id=row["product_id"],
        product_name=row["product_name"],
        product_price=row["product_price"],
        current_operation_id=(
            int(row["current_operation_id"])
            if row["current_operation_id"] is not None
            else None
        ),
        lock_status=LockStatus(row["lock_status"]),
        last_lock_event_at=row["last_lock_event_at"],
        updated_at=row["updated_at"],
    )
