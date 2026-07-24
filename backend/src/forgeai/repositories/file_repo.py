"""File data-access layer.

Thin async SQLAlchemy queries for the repository_files table.
Includes bulk insert and per-repository statistics aggregation.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.file import RepositoryFile

logger = structlog.get_logger(__name__)


class FileRepo:
    """CRUD + bulk operations for the ``repository_files`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def bulk_insert(self, rows: list[dict]) -> int:
        """Insert a batch of file rows, ignoring duplicates.

        Uses PostgreSQL ``INSERT ... ON CONFLICT DO NOTHING`` so re-scans
        are safe. Returns the number of rows actually inserted.

        Parameters
        ----------
        rows:
            List of dicts matching RepositoryFile column names.
        """
        if not rows:
            return 0

        stmt = (
            pg_insert(RepositoryFile)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_repo_file_path")
        )
        result = await self._db.execute(stmt)
        inserted = result.rowcount
        logger.info(
            "files_bulk_inserted",
            attempted=len(rows),
            inserted=inserted,
        )
        return inserted

    async def list_by_repo(
        self,
        repo_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[RepositoryFile], int]:
        """Return a paginated list of files and the total count.

        Parameters
        ----------
        repo_id:
            The owning repository UUID.
        page:
            1-based page number.
        page_size:
            Number of items per page (max 200 enforced here).
        """
        page_size = min(page_size, 200)
        offset = (page - 1) * page_size

        # Total count
        count_result = await self._db.execute(
            select(func.count()).where(RepositoryFile.repository_id == repo_id)
        )
        total: int = count_result.scalar_one()

        # Page of rows
        rows_result = await self._db.execute(
            select(RepositoryFile)
            .where(RepositoryFile.repository_id == repo_id)
            .order_by(RepositoryFile.relative_path)
            .offset(offset)
            .limit(page_size)
        )
        files = list(rows_result.scalars().all())

        return files, total

    async def get_stats(self, repo_id: UUID) -> dict:
        """Compute scan statistics directly from the database.

        Returns a dict with keys:
          total_files, code_files, total_size_bytes, languages
        """
        from forgeai.services.scanner import CODE_EXTENSIONS

        # All files for this repo
        result = await self._db.execute(
            select(
                RepositoryFile.language,
                RepositoryFile.extension,
                RepositoryFile.size,
            ).where(RepositoryFile.repository_id == repo_id)
        )
        rows = result.all()

        total_files = len(rows)
        total_size = sum(r.size for r in rows)
        code_files = sum(1 for r in rows if r.extension in CODE_EXTENSIONS)

        langs: dict[str, int] = {}
        for r in rows:
            if r.language:
                langs[r.language] = langs.get(r.language, 0) + 1

        return {
            "total_files": total_files,
            "code_files": code_files,
            "total_size_bytes": total_size,
            "languages": dict(
                sorted(langs.items(), key=lambda kv: kv[1], reverse=True)
            ),
        }

    async def delete_by_repo(self, repo_id: UUID) -> int:
        """Delete all file rows for a repository.

        Returns the number of deleted rows.
        Note: normally the CASCADE on the FK handles this; this method
        is provided for explicit bulk-delete without loading into memory.
        """
        result = await self._db.execute(
            delete(RepositoryFile).where(
                RepositoryFile.repository_id == repo_id
            )
        )
        return result.rowcount
