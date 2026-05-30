"""Repository for individual sales (purchases from a cell)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.database import get_connection
from app.domain.sales_status import SaleStatus

_SALE_COLUMNS = """
    id, limit_id, cell_number, product_id, product_name, price_kopecks,
    status, created_at, completed_at, failed_at, error_message
"""


@dataclass(frozen=True)
class SaleRecord:
    """A row of the sales table."""

    id: int
    limit_id: int
    cell_number: int
    product_id: str
    product_name: str
    price_kopecks: int
    status: SaleStatus
    created_at: str
    completed_at: str | None
    failed_at: str | None
    error_message: str | None


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class SaleRepository:
    """Data access for sales."""

    def create_opening_sale(
        self,
        *,
        limit_id: int,
        cell_number: int,
        product_id: str,
        product_name: str,
        price_kopecks: int,
    ) -> SaleRecord:
        """Create a sale in the OPENING status (before the cell opens)."""
        now = _utc_now_iso()
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sales (
                    limit_id, cell_number, product_id, product_name,
                    price_kopecks, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    limit_id,
                    cell_number,
                    product_id,
                    product_name,
                    price_kopecks,
                    SaleStatus.OPENING.value,
                    now,
                ),
            )
            sale_id = int(cursor.lastrowid)
            row = conn.execute(
                f"SELECT {_SALE_COLUMNS} FROM sales WHERE id = ?",
                (sale_id,),
            ).fetchone()
        return _row_to_record(row)

    def complete_sale(self, sale_id: int) -> SaleRecord:
        """Mark the sale as COMPLETED with completed_at = now."""
        now = _utc_now_iso()
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE sales
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (SaleStatus.COMPLETED.value, now, sale_id),
            )
            row = conn.execute(
                f"SELECT {_SALE_COLUMNS} FROM sales WHERE id = ?",
                (sale_id,),
            ).fetchone()
        return _row_to_record(row)

    def fail_sale(self, sale_id: int, error_message: str) -> SaleRecord:
        """Mark the sale as FAILED with failed_at = now and a reason."""
        now = _utc_now_iso()
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE sales
                SET status = ?, failed_at = ?, error_message = ?
                WHERE id = ?
                """,
                (SaleStatus.FAILED.value, now, error_message, sale_id),
            )
            row = conn.execute(
                f"SELECT {_SALE_COLUMNS} FROM sales WHERE id = ?",
                (sale_id,),
            ).fetchone()
        return _row_to_record(row)

    def get_sales_by_limit(self, limit_id: int) -> list[SaleRecord]:
        """All sales belonging to a given limit, oldest first."""
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {_SALE_COLUMNS} FROM sales
                WHERE limit_id = ?
                ORDER BY id
                """,
                (limit_id,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def _row_to_record(row) -> SaleRecord:
    return SaleRecord(
        id=int(row["id"]),
        limit_id=int(row["limit_id"]),
        cell_number=int(row["cell_number"]),
        product_id=row["product_id"],
        product_name=row["product_name"],
        price_kopecks=int(row["price_kopecks"]),
        status=SaleStatus(row["status"]),
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        failed_at=row["failed_at"],
        error_message=row["error_message"],
    )
