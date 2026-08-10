"""Symbol data-access layer.

Async SQLAlchemy queries for the symbols table.
Includes bulk insertion, filtered list queries, and per-repository statistics.

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.symbol import Symbol, SymbolType, Visibility

logger = structlog.get_logger(__name__)


class SymbolRepo:
    """CRUD + bulk operations for the ``symbols`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def bulk_insert(self, rows: list[dict]) -> int:
        """Insert a batch of symbol rows.

        Parameters
        ----------
        rows:
            List of dicts matching Symbol column names.

        Returns
        -------
        int
            Number of inserted symbol records.
        """
        if not rows:
            return 0

        stmt = pg_insert(Symbol).values(rows)
        result = await self._db.execute(stmt)
        inserted = result.rowcount
        logger.info(
            "symbols_bulk_inserted",
            attempted=len(rows),
            inserted=inserted,
        )
        return inserted

    async def get_by_id(self, symbol_id: UUID) -> Symbol | None:
        """Fetch a single symbol by its UUID primary key."""
        result = await self._db.execute(
            select(Symbol).where(Symbol.id == symbol_id)
        )
        return result.scalar_one_or_none()

    async def list_by_repo(
        self,
        repo_id: UUID,
        *,
        file_id: UUID | None = None,
        symbol_type: SymbolType | str | None = None,
        name_query: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Symbol], int]:
        """Return a paginated list of symbols matching filters and total count.

        Parameters
        ----------
        repo_id:
            Target repository UUID.
        file_id:
            Optional filter by specific file UUID.
        symbol_type:
            Optional filter by symbol type (e.g. SymbolType.function or 'function').
        name_query:
            Optional case-insensitive search string for symbol names.
        page:
            1-based page number.
        page_size:
            Number of items per page (max 200).
        """
        page_size = min(page_size, 200)
        offset = (page - 1) * page_size

        conditions = [Symbol.repository_id == repo_id]

        if file_id is not None:
            conditions.append(Symbol.file_id == file_id)
        if symbol_type is not None:
            if isinstance(symbol_type, str):
                symbol_type = SymbolType(symbol_type)
            conditions.append(Symbol.symbol_type == symbol_type)
        if name_query is not None and name_query.strip():
            conditions.append(Symbol.name.ilike(f"%{name_query.strip()}%"))

        # Total count query
        count_stmt = select(func.count()).where(*conditions)
        count_result = await self._db.execute(count_stmt)
        total: int = count_result.scalar_one()

        # Page query
        rows_stmt = (
            select(Symbol)
            .where(*conditions)
            .order_by(Symbol.file_id, Symbol.start_line, Symbol.name)
            .offset(offset)
            .limit(page_size)
        )
        rows_result = await self._db.execute(rows_stmt)
        symbols = list(rows_result.scalars().all())

        return symbols, total

    async def list_by_file(self, file_id: UUID) -> list[Symbol]:
        """Fetch all symbols defined in a specific file ordered by line position."""
        result = await self._db.execute(
            select(Symbol)
            .where(Symbol.file_id == file_id)
            .order_by(Symbol.start_line, Symbol.start_column)
        )
        return list(result.scalars().all())

    async def delete_by_repo(self, repo_id: UUID) -> int:
        """Delete all symbol rows associated with a repository."""
        result = await self._db.execute(
            delete(Symbol).where(Symbol.repository_id == repo_id)
        )
        return result.rowcount

    async def delete_by_file(self, file_id: UUID) -> int:
        """Delete all symbol rows associated with a file."""
        result = await self._db.execute(
            delete(Symbol).where(Symbol.file_id == file_id)
        )
        return result.rowcount

    async def count_by_repo(self, repo_id: UUID) -> int:
        """Get the total count of symbols in a repository."""
        result = await self._db.execute(
            select(func.count()).where(Symbol.repository_id == repo_id)
        )
        return result.scalar_one()

    async def get_stats_by_repo(self, repo_id: UUID) -> dict[str, int]:
        """Compute breakdown count of symbols grouped by symbol_type.

        Returns a dictionary mapping symbol type string to count.
        """
        result = await self._db.execute(
            select(Symbol.symbol_type, func.count())
            .where(Symbol.repository_id == repo_id)
            .group_by(Symbol.symbol_type)
        )
        rows = result.all()
        return {st.value: cnt for st, cnt in rows}
