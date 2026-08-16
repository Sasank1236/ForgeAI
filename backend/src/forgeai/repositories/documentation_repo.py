"""Documentation data-access layer.

Thin async SQLAlchemy queries for the documentation table.

Phase 8 — Auto Documentation Generation
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.documentation import DocStatus, DocType, Documentation

logger = structlog.get_logger(__name__)


class DocumentationRepo:
    """CRUD operations for the ``documentation`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_doc(
        self,
        repository_id: UUID,
        doc_type: DocType,
        title: str,
        content: str,
        file_path: str | None = None,
        status: DocStatus = DocStatus.generated,
    ) -> Documentation:
        """Create or update a generated documentation record."""
        # Upsert logic if doc_type exists for repository
        existing = await self.get_doc_by_type(repository_id, doc_type)
        if existing:
            existing.title = title
            existing.content = content
            existing.file_path = file_path
            existing.status = status
            await self._db.flush()
            logger.info("documentation_updated", doc_id=str(existing.id), type=doc_type)
            return existing

        doc = Documentation(
            repository_id=repository_id,
            doc_type=doc_type,
            title=title,
            content=content,
            file_path=file_path,
            status=status,
        )
        self._db.add(doc)
        await self._db.flush()
        logger.info(
            "documentation_created",
            doc_id=str(doc.id),
            repo_id=str(repository_id),
            type=doc_type,
        )
        return doc

    async def get_doc(self, doc_id: UUID) -> Documentation | None:
        """Fetch a single documentation record by UUID."""
        stmt = select(Documentation).where(Documentation.id == doc_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_doc_by_type(
        self,
        repository_id: UUID,
        doc_type: DocType,
    ) -> Documentation | None:
        """Fetch documentation for a repository by type."""
        stmt = select(Documentation).where(
            Documentation.repository_id == repository_id,
            Documentation.doc_type == doc_type,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_docs_by_repo(self, repository_id: UUID) -> list[Documentation]:
        """Fetch all documentation records for a repository."""
        stmt = (
            select(Documentation)
            .where(Documentation.repository_id == repository_id)
            .order_by(Documentation.updated_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_doc_content(
        self,
        doc_id: UUID,
        content: str,
        title: str | None = None,
    ) -> Documentation | None:
        """Update documentation content or title."""
        doc = await self.get_doc(doc_id)
        if doc:
            doc.content = content
            if title:
                doc.title = title
            doc.status = DocStatus.updated
            await self._db.flush()
        return doc

    async def delete_doc(self, doc_id: UUID) -> int:
        """Delete a documentation record."""
        stmt = delete(Documentation).where(Documentation.id == doc_id)
        result = await self._db.execute(stmt)
        return result.rowcount
