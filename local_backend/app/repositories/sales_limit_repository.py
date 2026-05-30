"""Repository for sales limits.

A sales limit caps how much (in kopecks) may be sold from the postamat
before an administrator resets it. Only one ``ACTIVE`` limit exists at a
time; setting a new one closes the previous (``CLOSED``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.database import get_connection
from app.domain.sales_status import SalesLimitStatus

_LIMIT_COLUMNS = """
    id, limit_amount_kopecks, sold_amount_kopecks, status,
    created_at, updated_at, closed_at
"""


@dataclass(frozen=True)
class SalesLimitRecord:
    """A row of the sales_limits table."""

    id: int
    limit_amount_kopecks: int
    sold_amount_kopecks: int
    status: SalesLimitStatus
    created_at: str
    updated_at: str
    closed_at: str | None

    @property
    def remaining_amount_kopecks(self) -> int:
        return max(0, self.limit_amount_kopecks - self.sold_amount_kopecks)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class SalesLimitRepository:
    """Data access for sales limits."""

    def get_active_limit(self) -> SalesLimitRecord | None:
        """Return the single ACTIVE limit, or ``None`` if none is set."""
        with get_connection() as conn:
            row = conn.execute(
                f"""
                SELECT {_LIMIT_COLUMNS} FROM sales_limits
                WHERE status = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (SalesLimitStatus.ACTIVE.value,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_record(row)

    def create_new_limit(self, limit_amount_kopecks: int) -> SalesLimitRecord:
        """Insert a fresh ACTIVE limit with sold_amount = 0."""
        now = _utc_now_iso()
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sales_limits (
                    limit_amount_kopecks, sold_amount_kopecks, status,
                    created_at, updated_at
                )
                VALUES (?, 0, ?, ?, ?)
                """,
                (
                    limit_amount_kopecks,
                    SalesLimitStatus.ACTIVE.value,
                    now,
                    now,
                ),
            )
            limit_id = int(cursor.lastrowid)
            row = conn.execute(
                f"SELECT {_LIMIT_COLUMNS} FROM sales_limits WHERE id = ?",
                (limit_id,),
            ).fetchone()
        return _row_to_record(row)

    def close_active_limit(self) -> None:
        """Mark every ACTIVE limit as CLOSED (there should be at most one)."""
        now = _utc_now_iso()
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE sales_limits
                SET status = ?, closed_at = ?, updated_at = ?
                WHERE status = ?
                """,
                (
                    SalesLimitStatus.CLOSED.value,
                    now,
                    now,
                    SalesLimitStatus.ACTIVE.value,
                ),
            )

    def increase_sold_amount(
        self, limit_id: int, amount_kopecks: int
    ) -> None:
        """Add ``amount_kopecks`` to the sold amount of the given limit."""
        now = _utc_now_iso()
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE sales_limits
                SET sold_amount_kopecks = sold_amount_kopecks + ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (amount_kopecks, now, limit_id),
            )

    def get_limit_summary(self) -> SalesLimitRecord | None:
        """Return the active limit record (or ``None``).

        Kept as a named method for the service layer; the service maps it
        to the API summary shape.
        """
        return self.get_active_limit()


def _row_to_record(row) -> SalesLimitRecord:
    return SalesLimitRecord(
        id=int(row["id"]),
        limit_amount_kopecks=int(row["limit_amount_kopecks"]),
        sold_amount_kopecks=int(row["sold_amount_kopecks"]),
        status=SalesLimitStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        closed_at=row["closed_at"],
    )
