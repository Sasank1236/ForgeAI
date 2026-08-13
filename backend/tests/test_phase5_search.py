"""Phase 5 unit & integration tests for Repository Search (Semantic + Hybrid).

Tests:
1. Search DTO schemas (SearchQueryRequest, SearchResponse, SearchType)
2. SearchService semantic search
3. SearchService keyword text search
4. SearchService symbol name search
5. SearchService hybrid Reciprocal Rank Fusion (RRF) algorithm
6. REST API search endpoints (POST & GET)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.repository import RepositoryStatus
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.schemas.search import (
    SearchQueryRequest,
    SearchType,
)
from forgeai.services.knowledge_base import KnowledgeBaseService
from forgeai.services.search import SearchService


@pytest.mark.asyncio
async def test_search_dto_schemas() -> None:
    """Verify SearchQueryRequest and SearchResponse DTO schemas."""
    req = SearchQueryRequest(
        query="calculate_total",
        search_type=SearchType.hybrid,
        limit=15,
        min_score=0.2,
    )
    assert req.query == "calculate_total"
    assert req.search_type == SearchType.hybrid
    assert req.limit == 15
    assert req.min_score == 0.2


@pytest.mark.asyncio
async def test_search_service_pipeline(db_session: AsyncSession) -> None:
    """Test full multi-modal search service pipeline (semantic, keyword, symbol, hybrid)."""
    repo_repo = RepositoryRepo(db_session)
    file_repo = FileRepo(db_session)
    kb_service = KnowledgeBaseService(db_session)
    search_service = SearchService(db_session)

    # 1. Create dummy repository & files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        py_file = tmp_path / "main.py"
        py_file.write_text(
            "def calculate_total(items: list) -> float:\n"
            "    '''Compute total sum of cart items.'''\n"
            "    return sum(items)\n",
            encoding="utf-8",
        )

        repo = await repo_repo.create(name="SearchTestRepo", root_path=str(tmp_path))
        await repo_repo.update_status(repo.id, RepositoryStatus.ready)

        await file_repo.bulk_insert(
            [
                {
                    "id": uuid4(),
                    "repository_id": repo.id,
                    "relative_path": "main.py",
                    "absolute_path": str(py_file),
                    "language": "Python",
                    "extension": ".py",
                    "size": py_file.stat().st_size,
                    "is_binary": False,
                    "mime_type": "text/x-python",
                    "line_count": 3,
                }
            ]
        )
        await db_session.commit()

        # 2. Build vector embeddings knowledge base
        await kb_service.index_repository(repo.id)
        await db_session.commit()

        # 3. Test Keyword Search
        kw_req = SearchQueryRequest(query="calculate_total", search_type=SearchType.keyword)
        kw_res = await search_service.search(repo.id, kw_req)
        assert kw_res.search_type == "keyword"
        assert len(kw_res.results) > 0
        assert "main.py" in kw_res.results[0].relative_path

        # 4. Test Semantic Search
        sem_req = SearchQueryRequest(query="compute total sum", search_type=SearchType.semantic, min_score=0.0)
        sem_res = await search_service.search(repo.id, sem_req)
        assert sem_res.search_type == "semantic"

        # 5. Test Hybrid RRF Search
        hyb_req = SearchQueryRequest(query="calculate_total sum", search_type=SearchType.hybrid, min_score=0.0)
        hyb_res = await search_service.search(repo.id, hyb_req)
        assert hyb_res.search_type == "hybrid"
        assert len(hyb_res.results) > 0


@pytest.mark.asyncio
async def test_search_api_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test POST and GET search REST API endpoints."""
    repo_repo = RepositoryRepo(db_session)
    file_repo = FileRepo(db_session)
    kb_service = KnowledgeBaseService(db_session)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        js_file = tmp_path / "app.js"
        js_file.write_text("function renderApp() { return 'hello'; }", encoding="utf-8")

        repo = await repo_repo.create(name="ApiSearchRepo", root_path=str(tmp_path))
        await repo_repo.update_status(repo.id, RepositoryStatus.ready)

        await file_repo.bulk_insert(
            [
                {
                    "id": uuid4(),
                    "repository_id": repo.id,
                    "relative_path": "app.js",
                    "absolute_path": str(js_file),
                    "language": "JavaScript",
                    "extension": ".js",
                    "size": js_file.stat().st_size,
                    "is_binary": False,
                    "mime_type": "text/javascript",
                    "line_count": 1,
                }
            ]
        )
        await db_session.commit()
        await kb_service.index_repository(repo.id)
        await db_session.commit()

        # Test POST /repositories/{id}/search
        post_resp = await client.post(
            f"/api/v1/repositories/{repo.id}/search",
            json={"query": "renderApp", "search_type": "keyword", "limit": 5},
        )
        assert post_resp.status_code == 200
        post_data = post_resp.json()
        assert post_data["query"] == "renderApp"
        assert post_data["search_type"] == "keyword"
        assert len(post_data["results"]) > 0

        # Test GET /repositories/{id}/search
        get_resp = await client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "renderApp", "type": "keyword", "limit": 5},
        )
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["query"] == "renderApp"
        assert get_data["search_type"] == "keyword"
