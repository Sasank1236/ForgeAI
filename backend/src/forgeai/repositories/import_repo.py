"""Import data-access layer.

Async SQLAlchemy queries for the imports table.
Includes bulk insertion and repository/file filtering.

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.import_ import Import, ImportType

logger = structlog.get_logger(__name__)


class ImportRepo:
    """CRUD + bulk operations for the ``imports`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def bulk_insert(self, rows: list[dict]) -> int:
        """Insert a batch of import rows.

        Parameters
        ----------
        rows:
            List of dicts matching Import column names.

        Returns
        -------
        int
            Number of inserted import records.
        """
        if not rows:
            return 0

        stmt = pg_insert(Import).values(rows)
        result = await self._db.execute(stmt)
        inserted = result.rowcount
        logger.info(
            "imports_bulk_inserted",
            attempted=len(rows),
            inserted=inserted,
        )
        return inserted

    async def get_by_id(self, import_id: UUID) -> Import | None:
        """Fetch a single import record by UUID primary key."""
        result = await self._db.execute(
            select(Import).where(Import.id == import_id)
        )
        return result.scalar_one_or_none()

    async def list_by_repo(
        self,
        repo_id: UUID,
        *,
        file_id: UUID | None = None,
        import_type: ImportType | str | None = None,
        module_query: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Import], int]:
        """Return a paginated list of import records matching filters and total count.

        Parameters
        ----------
        repo_id:
            Target repository UUID.
        file_id:
            Optional filter by file UUID.
        import_type:
            Optional filter by import type (e.g. ImportType.from_import).
        module_query:
            Optional case-insensitive search string for target module.
        page:
            1-based page number.
        page_size:
            Number of items per page (max 200).
        """
        page_size = min(page_size, 200)
        offset = (page - 1) * page_size

        conditions = [Import.repository_id == repo_id]

        if file_id is not None:
            conditions.append(Import.file_id == file_id)
        if import_type is not None:
            if isinstance(import_type, str):
                import_type = ImportType(import_type)
            conditions.append(Import.import_type == import_type)
        if module_query is not None and module_query.strip():
            conditions.append(Import.target_module.ilike(f"%{module_query.strip()}%"))

        # Total count query
        count_stmt = select(func.count()).where(*conditions)
        count_result = await self._db.execute(count_stmt)
        total: int = count_result.scalar_one()

        # Page query
        rows_stmt = (
            select(Import)
            .where(*conditions)
            .order_by(Import.file_id, Import.target_module)
            .offset(offset)
            .limit(page_size)
        )
        rows_result = await self._db.execute(rows_stmt)
        imports = list(rows_result.scalars().all())

        return imports, total

    async def list_by_file(self, file_id: UUID) -> list[Import]:
        """Fetch all imports in a specific file."""
        result = await self._db.execute(
            select(Import)
            .where(Import.file_id == file_id)
            .order_by(Import.target_module)
        )
        return list(result.scalars().all())

    async def delete_by_repo(self, repo_id: UUID) -> int:
        """Delete all import records associated with a repository."""
        result = await self._db.execute(
            delete(Import).where(Import.repository_id == repo_id)
        )
        return result.rowcount

    async def delete_by_file(self, file_id: UUID) -> int:
        """Delete all import records associated with a file."""
        result = await self._db.execute(
            delete(Import).where(Import.file_id == file_id)
        )
        return result.rowcount

    async def count_by_repo(self, repo_id: UUID) -> int:
        """Get the total count of import records in a repository."""
        result = await self._db.execute(
            select(func.count()).where(Import.repository_id == repo_id)
        )
        return result.scalar_one()
