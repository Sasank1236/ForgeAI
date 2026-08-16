"""Phase 8 unit & integration tests for Auto Documentation Generation.

Tests:
1. Documentation ORM model
2. DocumentationRepo CRUD operations
3. DocumentationService documentation synthesis flow
4. REST API documentation endpoints
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.documentation import DocStatus, DocType
from forgeai.models.repository import RepositoryStatus
from forgeai.repositories.documentation_repo import DocumentationRepo
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.repositories.symbol_repo import SymbolRepo
from forgeai.schemas.documentation import DocGenerateRequest
from forgeai.services.documentation_service import DocumentationService


@pytest.mark.asyncio
async def test_documentation_repo_crud(db_session: AsyncSession) -> None:
    """Test DocumentationRepo create, get by type, list, update, and delete."""
    repo_repo = RepositoryRepo(db_session)
    doc_repo = DocumentationRepo(db_session)

    repository = await repo_repo.create(name="DocRepoTest", root_path="/tmp/doctest")
    await db_session.commit()

    # Create doc
    doc = await doc_repo.create_doc(
        repository_id=repository.id,
        doc_type=DocType.readme,
        title="README — DocRepoTest",
        content="# DocRepoTest Overview\n\nSample readme content.",
        file_path="README.md",
    )
    await db_session.commit()

    assert doc.id is not None
    assert doc.doc_type == DocType.readme
    assert doc.status == DocStatus.generated

    # Fetch by type
    fetched = await doc_repo.get_doc_by_type(repository.id, DocType.readme)
    assert fetched is not None
    assert fetched.id == doc.id

    # List by repo
    docs = await doc_repo.list_docs_by_repo(repository.id)
    assert len(docs) == 1

    # Update content
    updated = await doc_repo.update_doc_content(
        doc.id,
        content="# Updated README\n\nNew content.",
        title="Updated README",
    )
    await db_session.commit()
    assert updated is not None
    assert updated.status == DocStatus.updated
    assert "Updated" in updated.title

    # Delete doc
    deleted_count = await doc_repo.delete_doc(doc.id)
    await db_session.commit()
    assert deleted_count == 1


@pytest.mark.asyncio
async def test_documentation_service_synthesis(db_session: AsyncSession) -> None:
    """Test DocumentationService README, Architecture, and API Reference generation."""
    repo_repo = RepositoryRepo(db_session)
    file_repo = FileRepo(db_session)
    symbol_repo = SymbolRepo(db_session)
    doc_service = DocumentationService(db_session)

    repository = await repo_repo.create(name="SynthDocRepo", root_path="/tmp/synthdoc")
    await repo_repo.update_status(repository.id, RepositoryStatus.ready)

    file_id = uuid4()
    await file_repo.bulk_insert(
        [
            {
                "id": file_id,
                "repository_id": repository.id,
                "relative_path": "src/auth.py",
                "absolute_path": "/tmp/synthdoc/src/auth.py",
                "language": "Python",
                "extension": ".py",
                "size": 128,
                "is_binary": False,
                "mime_type": "text/x-python",
                "line_count": 10,
            }
        ]
    )
    await symbol_repo.bulk_insert(
        [
            {
                "file_id": file_id,
                "repository_id": repository.id,
                "name": "login_user",
                "symbol_type": "function",
                "language": "Python",
                "start_line": 1,
                "end_line": 10,
                "visibility": "public",
                "signature": "def login_user(username: str) -> bool:",
            }
        ]
    )
    await db_session.commit()

    # 1. Generate README
    readme_dto = await doc_service.generate_documentation(
        repository.id,
        DocGenerateRequest(doc_type=DocType.readme),
    )
    assert readme_dto.doc_type == DocType.readme
    assert "SynthDocRepo" in readme_dto.content
    assert "login_user" in readme_dto.content

    # 2. Generate Architecture
    arch_dto = await doc_service.generate_documentation(
        repository.id,
        DocGenerateRequest(doc_type=DocType.architecture),
    )
    assert arch_dto.doc_type == DocType.architecture
    assert "Architecture" in arch_dto.title

    # 3. Generate API Reference
    api_dto = await doc_service.generate_documentation(
        repository.id,
        DocGenerateRequest(doc_type=DocType.api_reference),
    )
    assert api_dto.doc_type == DocType.api_reference
    assert "login_user" in api_dto.content


@pytest.mark.asyncio
async def test_documentation_api_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test Documentation REST API endpoints (generate, list, get, put, delete)."""
    repo_repo = RepositoryRepo(db_session)

    repository = await repo_repo.create(name="ApiDocRepo", root_path="/tmp/apidoc")
    await repo_repo.update_status(repository.id, RepositoryStatus.ready)
    await db_session.commit()

    # 1. Generate Doc
    gen_resp = await client.post(
        f"/api/v1/repositories/{repository.id}/docs/generate",
        json={"doc_type": "readme", "title": "API Doc Title"},
    )
    assert gen_resp.status_code == 201
    doc_id = gen_resp.json()["id"]

    # 2. List Docs
    list_resp = await client.get(f"/api/v1/repositories/{repository.id}/docs")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    # 3. Get Doc Details
    get_resp = await client.get(f"/api/v1/docs/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "API Doc Title"

    # 4. Update Doc
    put_resp = await client.put(
        f"/api/v1/docs/{doc_id}",
        json={"content": "# Modified Documentation Content", "title": "Updated Title"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["title"] == "Updated Title"

    # 5. Delete Doc
    del_resp = await client.delete(f"/api/v1/docs/{doc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
