"""CodeEmbedding data-access layer.

Async SQLAlchemy queries for the code_embeddings table.
Includes bulk insertion, vector similarity search via pgvector, and stats aggregation.

Phase 4 — Vector Embeddings & Knowledge Base
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.embedding import ChunkType, CodeEmbedding
from forgeai.models.file import RepositoryFile

logger = structlog.get_logger(__name__)


class EmbeddingRepo:
    """CRUD + vector search operations for the ``code_embeddings`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def bulk_insert(self, rows: list[dict]) -> int:
        """Insert a batch of code embedding rows.

        Parameters
        ----------
        rows:
            List of dicts matching CodeEmbedding column names.

        Returns
        -------
        int
            Number of inserted embedding records.
        """
        if not rows:
            return 0

        stmt = pg_insert(CodeEmbedding).values(rows)
        result = await self._db.execute(stmt)
        inserted = result.rowcount
        logger.info(
            "embeddings_bulk_inserted",
            attempted=len(rows),
            inserted=inserted,
        )
        return inserted

    async def get_by_id(self, embedding_id: UUID) -> CodeEmbedding | None:
        """Fetch a single embedding record by UUID primary key."""
        result = await self._db.execute(
            select(CodeEmbedding).where(CodeEmbedding.id == embedding_id)
        )
        return result.scalar_one_or_none()

    async def cosine_similarity_search(
        self,
        repo_id: UUID,
        query_vector: list[float],
        *,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> list[tuple[CodeEmbedding, RepositoryFile, float]]:
        """Perform vector cosine similarity search over a repository's code embeddings.

        Parameters
        ----------
        repo_id:
            Target repository UUID.
        query_vector:
            1536-dimensional float vector query.
        limit:
            Maximum number of top search hits to return (max 100).
        min_similarity:
            Minimum cosine similarity threshold (0.0 to 1.0).

        Returns
        -------
        list[tuple[CodeEmbedding, RepositoryFile, float]]
            List of tuples: (CodeEmbedding, RepositoryFile, similarity_score).
        """
        limit = min(limit, 100)

        # Check database dialect to support SQLite unit tests gracefully
        dialect_name = self._db.bind.dialect.name if self._db.bind else ""
        if dialect_name == "sqlite":
            stmt = (
                select(CodeEmbedding, RepositoryFile)
                .join(RepositoryFile, CodeEmbedding.file_id == RepositoryFile.id)
                .where(CodeEmbedding.repository_id == repo_id)
            )
            result = await self._db.execute(stmt)
            rows = result.all()

            scored_hits: list[tuple[CodeEmbedding, RepositoryFile, float]] = []
            for emb, file in rows:
                vec = emb.embedding
                if isinstance(vec, list) and len(vec) == len(query_vector):
                    sim = sum(a * b for a, b in zip(vec, query_vector, strict=False))
                else:
                    sim = 0.0
                if sim >= min_similarity:
                    scored_hits.append((emb, file, float(sim)))

            scored_hits.sort(key=lambda x: x[2], reverse=True)
            return scored_hits[:limit]

        # PostgreSQL distance calculation via pgvector
        distance_expr = CodeEmbedding.embedding.cosine_distance(query_vector)
        similarity_expr = (1.0 - distance_expr).label("similarity")

        stmt = (
            select(CodeEmbedding, RepositoryFile, similarity_expr)
            .join(RepositoryFile, CodeEmbedding.file_id == RepositoryFile.id)
            .where(CodeEmbedding.repository_id == repo_id)
            .order_by(distance_expr.asc())
            .limit(limit)
        )

        result = await self._db.execute(stmt)
        rows = result.all()

        hits: list[tuple[CodeEmbedding, RepositoryFile, float]] = []
        for emb, file, sim in rows:
            sim_score = float(sim) if sim is not None else 0.0
            if sim_score >= min_similarity:
                hits.append((emb, file, sim_score))

        return hits

    async def list_by_file(self, file_id: UUID) -> list[CodeEmbedding]:
        """Fetch all chunk embeddings for a specific file ordered by chunk_index."""
        result = await self._db.execute(
            select(CodeEmbedding)
            .where(CodeEmbedding.file_id == file_id)
            .order_by(CodeEmbedding.chunk_index)
        )
        return list(result.scalars().all())

    async def delete_by_repo(self, repo_id: UUID) -> int:
        """Delete all embedding rows associated with a repository."""
        result = await self._db.execute(
            delete(CodeEmbedding).where(CodeEmbedding.repository_id == repo_id)
        )
        return result.rowcount

    async def delete_by_file(self, file_id: UUID) -> int:
        """Delete all embedding rows associated with a file."""
        result = await self._db.execute(
            delete(CodeEmbedding).where(CodeEmbedding.file_id == file_id)
        )
        return result.rowcount

    async def count_by_repo(self, repo_id: UUID) -> int:
        """Get the total count of embedding chunk records in a repository."""
        result = await self._db.execute(
            select(func.count()).where(CodeEmbedding.repository_id == repo_id)
        )
        return result.scalar_one()

    async def get_stats_by_repo(self, repo_id: UUID) -> dict:
        """Compute indexing statistics directly from the database.

        Returns dict:
          total_chunks, total_embedded_files, total_tokens, by_chunk_type
        """
        # Count distinct files embedded
        distinct_files_res = await self._db.execute(
            select(func.count(func.distinct(CodeEmbedding.file_id))).where(
                CodeEmbedding.repository_id == repo_id
            )
        )
        embedded_files = distinct_files_res.scalar_one()

        # Group by chunk_type and sum tokens
        stats_res = await self._db.execute(
            select(
                CodeEmbedding.chunk_type,
                func.count(),
                func.coalesce(func.sum(CodeEmbedding.token_count), 0),
            )
            .where(CodeEmbedding.repository_id == repo_id)
            .group_by(CodeEmbedding.chunk_type)
        )
        rows = stats_res.all()

        total_chunks = sum(cnt for _, cnt, _ in rows)
        total_tokens = sum(int(tokens) for _, _, tokens in rows)

        by_type: dict[str, int] = {}
        for ct, cnt, _ in rows:
            by_type[ct.value if isinstance(ct, ChunkType) else str(ct)] = cnt

        return {
            "total_chunks": total_chunks,
            "total_embedded_files": embedded_files,
            "total_tokens": total_tokens,
            "by_chunk_type": by_type,
        }
