"""Phase 6 unit & integration tests for Repository Chat & Grounded QA.

Tests:
1. ChatSession & ChatMessage ORM models
2. ChatRepo CRUD operations
3. ContextBuilderService grounded prompt context construction
4. ChatService multi-turn messaging & fallback LLM generation
5. REST API chat endpoints (POST/GET/DELETE sessions, POST message & stream)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.chat import MessageRole
from forgeai.models.repository import RepositoryStatus
from forgeai.repositories.chat_repo import ChatRepo
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.schemas.chat import (
    ChatMessageCreate,
    ChatSessionCreate,
)
from forgeai.services.chat_service import ChatService
from forgeai.services.context_builder import ContextBuilderService
from forgeai.services.knowledge_base import KnowledgeBaseService


@pytest.mark.asyncio
async def test_chat_repo_crud(db_session: AsyncSession) -> None:
    """Test ChatRepo session creation, message appending, listing, and deletion."""
    repo_repo = RepositoryRepo(db_session)
    chat_repo = ChatRepo(db_session)

    repository = await repo_repo.create(name="ChatRepoTest", root_path="/tmp/test")
    await db_session.commit()

    # Create session
    session = await chat_repo.create_session(repository.id, title="Test Chat Session")
    await db_session.commit()

    assert session.id is not None
    assert session.title == "Test Chat Session"

    # Add messages
    user_msg = await chat_repo.add_message(
        session_id=session.id,
        role=MessageRole.user,
        content="How does authentication work?",
    )
    assistant_msg = await chat_repo.add_message(
        session_id=session.id,
        role=MessageRole.assistant,
        content="Authentication uses JWT tokens.",
        citations=[{"relative_path": "auth.py", "start_line": 10, "end_line": 25}],
    )
    await db_session.commit()

    assert user_msg.role == MessageRole.user
    assert assistant_msg.role == MessageRole.assistant

    # List messages
    messages = await chat_repo.list_messages(session.id)
    assert len(messages) == 2
    assert messages[0].content == "How does authentication work?"
    assert messages[1].content == "Authentication uses JWT tokens."

    # Delete session
    deleted_count = await chat_repo.delete_session(session.id)
    await db_session.commit()
    assert deleted_count == 1


@pytest.mark.asyncio
async def test_context_builder_and_chat_service(db_session: AsyncSession) -> None:
    """Test ContextBuilderService and ChatService grounded answer generation."""
    repo_repo = RepositoryRepo(db_session)
    file_repo = FileRepo(db_session)
    kb_service = KnowledgeBaseService(db_session)
    chat_service = ChatService(db_session)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        py_file = tmp_path / "auth.py"
        py_file.write_text(
            "def authenticate_user(token: str) -> bool:\n"
            "    '''Validate JWT bearer token.'''\n"
            "    return token == 'valid_token'\n",
            encoding="utf-8",
        )

        repo = await repo_repo.create(name="GroundedChatRepo", root_path=str(tmp_path))
        await repo_repo.update_status(repo.id, RepositoryStatus.ready)

        await file_repo.bulk_insert(
            [
                {
                    "id": uuid4(),
                    "repository_id": repo.id,
                    "relative_path": "auth.py",
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
        await kb_service.index_repository(repo.id)
        await db_session.commit()

        # 1. Test ContextBuilderService
        builder = ContextBuilderService(db_session)
        ctx, citations = await builder.build_grounded_context(repo.id, "authenticate_user token")
        assert "auth.py" in ctx

        # 2. Test ChatService
        sess_dto = await chat_service.create_session(repo.id, ChatSessionCreate(title="Auth QA"))
        msg_req = ChatMessageCreate(content="How is authenticate_user defined?")
        msg_dto = await chat_service.send_message(sess_dto.id, msg_req)

        assert msg_dto.role == MessageRole.assistant
        assert len(msg_dto.content) > 0


@pytest.mark.asyncio
async def test_chat_api_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test Chat REST API endpoints (sessions CRUD & message sending)."""
    repo_repo = RepositoryRepo(db_session)

    repo = await repo_repo.create(name="ApiChatRepo", root_path="/tmp/apichat")
    await repo_repo.update_status(repo.id, RepositoryStatus.ready)
    await db_session.commit()

    # 1. Create Session
    create_resp = await client.post(
        f"/api/v1/repositories/{repo.id}/chat/sessions",
        json={"title": "API Test Session"},
    )
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    # 2. List Sessions
    list_resp = await client.get(f"/api/v1/repositories/{repo.id}/chat/sessions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    # 3. Send Message
    msg_resp = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Explain project setup", "search_type": "keyword"},
    )
    assert msg_resp.status_code == 200
    assert msg_resp.json()["role"] == "assistant"

    # 4. Stream Message (SSE)
    stream_resp = await client.post(
        f"/api/v1/chat/sessions/{session_id}/stream",
        json={"content": "Stream response test", "search_type": "keyword"},
    )
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]

    # 5. Delete Session
    del_resp = await client.delete(f"/api/v1/chat/sessions/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
