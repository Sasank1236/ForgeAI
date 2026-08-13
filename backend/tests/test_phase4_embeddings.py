"""Phase 4 unit & integration tests for Vector Embeddings & Knowledge Base.

Tests:
1. EmbeddingService (1536-dim deterministic vectors, L2 norm, query embedding)
2. CodeChunker (sliding window, AST symbol chunking, line bounds)
3. EmbeddingRepo & KnowledgeBaseService (vector storage, similarity search)
4. Phase 4 API v1 REST endpoints (POST index, GET stats, DELETE index, POST search)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from forgeai.models.embedding import ChunkType
from forgeai.models.repository import RepositoryStatus
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.schemas.embedding import IndexRequest
from forgeai.services.chunker import CodeChunker
from forgeai.services.embedding import EMBEDDING_DIMENSION, EmbeddingService
from forgeai.services.knowledge_base import KnowledgeBaseService


@pytest.mark.asyncio
async def test_embedding_service_mock_vector_properties() -> None:
    """Verify EmbeddingService produces deterministic float vectors."""
    svc = EmbeddingService()

    # Generate vector for sample string
    vec = await svc.generate_query_embedding("def calculate_total(): return 42")

    assert len(vec) == EMBEDDING_DIMENSION
    assert isinstance(vec[0], float)

    # L2 norm check
    l2_norm = sum(x * x for x in vec) ** 0.5
    assert abs(l2_norm - 1.0) < 1e-4

    # Deterministic consistency test
    vec2 = await svc.generate_query_embedding("def calculate_total(): return 42")
    assert vec == vec2


@pytest.mark.asyncio
async def test_code_chunker_sliding_window() -> None:
    """Test CodeChunker sliding window fallback chunking logic."""
    chunker = CodeChunker(default_chunk_size=128, default_overlap=32)

    sample_code = "\n".join([f"line_{i} = {i}" for i in range(100)])
    repo_id = uuid4()
    file_id = uuid4()

    chunks = chunker.chunk_file(
        repo_id=repo_id,
        file_id=file_id,
        relative_path="src/main.py",
        content=sample_code,
        symbols=None,
    )

    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert first_chunk.repository_id == repo_id
    assert first_chunk.file_id == file_id
    assert first_chunk.chunk_type == ChunkType.window
    assert first_chunk.start_line == 1
    assert "src/main.py" in first_chunk.chunk_text


@pytest.mark.asyncio
async def test_knowledge_base_service_flow(db_session: AsyncSession) -> None:
    """Integration test for repository vector indexing and semantic search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        py_file = tmp_path / "app.py"
        py_file.write_text(
            "def calculate_total(prices: list[float]) -> float:\n"
            "    '''Calculate total sum of prices.'''\n"
            "    return sum(prices)\n",
            encoding="utf-8",
        )

        # 1. Create repository row
        repo_repo = RepositoryRepo(db_session)
        file_repo = FileRepo(db_session)

        repo = await repo_repo.create(
            name="TestKbRepo",
            root_path=str(tmp_path),
        )
        await repo_repo.update_status(repo.id, RepositoryStatus.ready)

        # 2. Insert repository file record
        await file_repo.bulk_insert(
            [
                {
                    "id": uuid4(),
                    "repository_id": repo.id,
                    "relative_path": "app.py",
                    "absolute_path": str(py_file),
                    "language": "Python",
                    "extension": ".py",
                    "size": py_file.stat().st_size,
                    "is_binary": False,
                    "line_count": 3,
                }
            ]
        )
        await db_session.commit()

        # 3. Index repository via KnowledgeBaseService
        kb_svc = KnowledgeBaseService(db_session)
        index_res = await kb_svc.index_repository(
            repo.id, IndexRequest(force_reindex=True)
        )

        assert index_res.repository_id == repo.id
        assert index_res.status == "indexed"
        assert index_res.stats.total_chunks > 0

        # 4. Perform vector similarity search
        hits = await kb_svc.search_similar(
            repo_id=repo.id,
            query="calculate total prices sum",
            limit=5,
            min_similarity=-1.0,
        )

        assert len(hits) > 0
        assert hits[0].repository_id == repo.id
        assert hits[0].relative_path == "app.py"

        # 5. Check index stats & clearing index
        stats = await kb_svc.get_index_stats(repo.id)
        assert stats.total_chunks > 0

        cleared = await kb_svc.clear_index(repo.id)
        assert cleared == index_res.stats.total_chunks


@pytest.mark.asyncio
async def test_phase4_api_endpoints(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    """Test REST API v1 endpoints for Knowledge Base indexing and search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        code_file = tmp_path / "service.py"
        code_file.write_text(
            "class UserService:\n"
            "    async def get_user(self, user_id: str):\n"
            "        return {'id': user_id, 'name': 'Alice'}\n",
            encoding="utf-8",
        )

        # Setup repo & file
        repo_repo = RepositoryRepo(db_session)
        file_repo = FileRepo(db_session)

        repo = await repo_repo.create(
            name="ApiTestRepo",
            root_path=str(tmp_path),
        )
        await repo_repo.update_status(repo.id, RepositoryStatus.ready)

        await file_repo.bulk_insert(
            [
                {
                    "id": uuid4(),
                    "repository_id": repo.id,
                    "relative_path": "service.py",
                    "absolute_path": str(code_file),
                    "language": "Python",
                    "extension": ".py",
                    "size": code_file.stat().st_size,
                    "is_binary": False,
                    "line_count": 3,
                }
            ]
        )
        await db_session.commit()

        # 1. POST /api/v1/repositories/{id}/index
        idx_resp = await client.post(
            f"/api/v1/repositories/{repo.id}/index",
            json={"force_reindex": True, "chunk_size": 256},
        )
        assert idx_resp.status_code == 200
        idx_json = idx_resp.json()
        assert idx_json["status"] == "indexed"
        assert idx_json["stats"]["total_chunks"] > 0

        # 2. GET /api/v1/repositories/{id}/index/stats
        stats_resp = await client.get(f"/api/v1/repositories/{repo.id}/index/stats")
        assert stats_resp.status_code == 200
        assert stats_resp.json()["total_chunks"] > 0

        # 3. POST /api/v1/repositories/{id}/search
        search_resp = await client.post(
            f"/api/v1/repositories/{repo.id}/search",
            json={
                "query": "UserService get_user Alice",
                "limit": 5,
                "min_similarity": -1.0,
            },
        )
        assert search_resp.status_code == 200
        search_json = search_resp.json()
        assert search_json["total_hits"] > 0
        assert search_json["results"][0]["relative_path"] == "service.py"

        # 4. DELETE /api/v1/repositories/{id}/index
        del_resp = await client.delete(f"/api/v1/repositories/{repo.id}/index")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] > 0
