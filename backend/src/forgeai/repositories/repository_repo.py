"""Repository data-access layer.

Thin async SQLAlchemy queries with no business logic.
All methods accept an AsyncSession and return typed results.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.repository import Repository, RepositoryStatus

logger = structlog.get_logger(__name__)


class RepositoryRepo:
    """CRUD operations for the ``repositories`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, name: str, root_path: str) -> Repository:
        """Insert a new repository row in ``pending`` status."""
        repo = Repository(name=name, root_path=root_path)
        self._db.add(repo)
        await self._db.flush()  # Assign id without committing
        logger.info("repo_created", repo_id=str(repo.id), name=name)
        return repo

    async def get_by_id(self, repo_id: UUID) -> Repository | None:
        """Fetch a single repository by UUID; returns None if not found."""
        result = await self._db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        return result.scalar_one_or_none()

    async def get_by_path(self, root_path: str) -> Repository | None:
        """Fetch a repository by its root_path (unique); returns None if not found."""
        result = await self._db.execute(
            select(Repository).where(Repository.root_path == root_path)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Repository]:
        """Return all repositories ordered by created_at descending."""
        result = await self._db.execute(
            select(Repository).order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        repo_id: UUID,
        status: RepositoryStatus,
        *,
        last_scanned: datetime | None = None,
        increment_scan_version: bool = False,
        default_branch: str | None = None,
        current_commit: str | None = None,
        git_remote: str | None = None,
    ) -> None:
        """Update mutable fields after a scan completes or fails."""
        values: dict = {"status": status}
        if last_scanned is not None:
            values["last_scanned"] = last_scanned
        if increment_scan_version:
            # Use ORM expression-level increment for concurrency safety
            values["scan_version"] = Repository.scan_version + 1  # type: ignore[assignment]
        if default_branch is not None:
            values["default_branch"] = default_branch
        if current_commit is not None:
            values["current_commit"] = current_commit
        if git_remote is not None:
            values["git_remote"] = git_remote

        await self._db.execute(
            update(Repository).where(Repository.id == repo_id).values(**values)
        )

    async def delete(self, repo_id: UUID) -> bool:
        """Delete a repository and its files (CASCADE).

        Returns True if a row was deleted, False if not found.
        """
        repo = await self.get_by_id(repo_id)
        if repo is None:
            return False
        await self._db.delete(repo)
        logger.info("repo_deleted", repo_id=str(repo_id))
        return True
