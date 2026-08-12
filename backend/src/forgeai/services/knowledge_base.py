"""Knowledge Base orchestration service.

Orchestrates code chunking, vector embedding generation, pgvector storage,
and knowledge base indexing for imported repositories.

Phase 4 — Vector Embeddings & Knowledge Base
"""

from __future__ import annotations

import time
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.embedding import ChunkType
from forgeai.repositories.embedding_repo import EmbeddingRepo
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.repositories.symbol_repo import SymbolRepo
from forgeai.schemas.embedding import (
    EmbeddingSearchResult,
    IndexRequest,
    IndexResponse,
    IndexStatsResponse,
)
from forgeai.services.chunker import CodeChunker
from forgeai.services.embedding import EmbeddingService

logger = structlog.get_logger(__name__)


class KnowledgeBaseService:
    """Orchestrates vector indexing and knowledge base search for repositories."""

    def __init__(
        self,
        db: AsyncSession,
        chunker: CodeChunker | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._db = db
        self._embedding_repo = EmbeddingRepo(db)
        self._file_repo = FileRepo(db)
        self._symbol_repo = SymbolRepo(db)
        self._repo = RepositoryRepo(db)
        self._chunker = chunker or CodeChunker()
        self._embedding_service = embedding_service or EmbeddingService()

    async def index_repository(
        self,
        repo_id: UUID,
        request: IndexRequest | None = None,
    ) -> IndexResponse:
        """Index a repository's source files into 1536-dim vector embeddings.

        Parameters
        ----------
        repo_id:
            Target repository UUID.
        request:
            Optional indexing options (force_reindex, chunk_size, overlap).

        Returns
        -------
        IndexResponse
            Contains index execution statistics.
        """
        start_time = time.perf_counter()
        req = request or IndexRequest()

        repo = await self._repo.get_by_id(repo_id)
        if repo is None:
            raise ValueError(f"Repository {repo_id} not found.")

        # If force_reindex, delete existing embeddings
        if req.force_reindex:
            deleted_count = await self._embedding_repo.delete_by_repo(repo_id)
            logger.info("knowledge_base_index_cleared", repo_id=str(repo_id), deleted=deleted_count)

        # List all files for repository
        files, _ = await self._file_repo.list_by_repo(repo_id, page=1, page_size=10000)
        repo_path = Path(repo.root_path)

        total_chunks = 0
        total_embedded_files = 0
        total_tokens = 0
        by_type: dict[str, int] = {}
        pending_rows: list[dict] = []

        for file in files:
            # Skip binary files or non-code files
            if file.is_binary:
                continue

            # Read file content safely
            abs_path = Path(file.absolute_path)
            if not abs_path.is_file():
                continue

            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except Exception as err:
                logger.warning(
                    "read_file_failed_for_indexing",
                    file_id=str(file.id),
                    path=file.relative_path,
                    error=str(err),
                )
                continue

            # Fetch symbols for file if parsed
            symbols = await self._symbol_repo.list_by_file(file.id)

            # Generate chunks
            chunks = self._chunker.chunk_file(
                repo_id=repo_id,
                file_id=file.id,
                relative_path=file.relative_path,
                content=content,
                symbols=symbols,
                chunk_size=req.chunk_size,
                overlap=req.overlap,
            )

            if not chunks:
                continue

            # Generate embeddings for chunks
            chunk_texts = [c.chunk_text for c in chunks]
            vectors = await self._embedding_service.generate_embeddings(chunk_texts)

            total_embedded_files += 1

            for chunk, vec in zip(chunks, vectors):
                total_chunks += 1
                total_tokens += chunk.token_count

                chunk_type_str = (
                    chunk.chunk_type.value
                    if isinstance(chunk.chunk_type, ChunkType)
                    else str(chunk.chunk_type)
                )
                by_type[chunk_type_str] = by_type.get(chunk_type_str, 0) + 1

                pending_rows.append(
                    {
                        "repository_id": repo_id,
                        "file_id": file.id,
                        "symbol_id": chunk.symbol_id,
                        "chunk_index": chunk.chunk_index,
                        "chunk_text": chunk.chunk_text,
                        "token_count": chunk.token_count,
                        "chunk_type": chunk.chunk_type,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "embedding": vec,
                    }
                )

            # Flush batch to DB if buffer > 200 rows
            if len(pending_rows) >= 200:
                await self._embedding_repo.bulk_insert(pending_rows)
                pending_rows.clear()

        # Insert remaining rows
        if pending_rows:
            await self._embedding_repo.bulk_insert(pending_rows)
            pending_rows.clear()

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        stats = IndexStatsResponse(
            total_chunks=total_chunks,
            total_embedded_files=total_embedded_files,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            by_chunk_type=by_type,
        )

        logger.info(
            "knowledge_base_indexing_complete",
            repo_id=str(repo_id),
            total_chunks=total_chunks,
            duration_ms=duration_ms,
        )

        return IndexResponse(
            repository_id=repo_id,
            status="indexed",
            stats=stats,
        )

    async def search_similar(
        self,
        repo_id: UUID,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> list[EmbeddingSearchResult]:
        """Perform semantic vector search against a repository's knowledge base."""
        query_vector = await self._embedding_service.generate_query_embedding(query)
        hits = await self._embedding_repo.cosine_similarity_search(
            repo_id=repo_id,
            query_vector=query_vector,
            limit=limit,
            min_similarity=min_similarity,
        )

        results: list[EmbeddingSearchResult] = []
        for emb, file, sim in hits:
            chunk_type_str = (
                emb.chunk_type.value
                if isinstance(emb.chunk_type, ChunkType)
                else str(emb.chunk_type)
            )
            results.append(
                EmbeddingSearchResult(
                    id=emb.id,
                    repository_id=emb.repository_id,
                    file_id=emb.file_id,
                    relative_path=file.relative_path,
                    symbol_id=emb.symbol_id,
                    chunk_index=emb.chunk_index,
                    chunk_type=chunk_type_str,
                    chunk_text=emb.chunk_text,
                    start_line=emb.start_line,
                    end_line=emb.end_line,
                    token_count=emb.token_count,
                    similarity=sim,
                )
            )

        return results

    async def get_index_stats(self, repo_id: UUID) -> IndexStatsResponse:
        """Fetch current vector index stats for a repository."""
        raw_stats = await self._embedding_repo.get_stats_by_repo(repo_id)
        return IndexStatsResponse(
            total_chunks=raw_stats.get("total_chunks", 0),
            total_embedded_files=raw_stats.get("total_embedded_files", 0),
            total_tokens=raw_stats.get("total_tokens", 0),
            duration_ms=0,
            by_chunk_type=raw_stats.get("by_chunk_type", {}),
        )

    async def clear_index(self, repo_id: UUID) -> int:
        """Clear all vector embeddings for a repository."""
        return await self._embedding_repo.delete_by_repo(repo_id)
