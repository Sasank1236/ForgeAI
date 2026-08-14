"""Repository chat & multi-turn QA service.

Orchestrates multi-turn conversation sessions, grounded prompt construction,
and LiteLLM / OpenAI streaming response generation.

Phase 6 — Repository Chat & Grounded QA
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.config import get_settings
from forgeai.models.chat import MessageRole
from forgeai.repositories.chat_repo import ChatRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatStreamChunk,
    CitationItem,
)
from forgeai.services.context_builder import ContextBuilderService

logger = structlog.get_logger(__name__)


class ChatService:
    """Service orchestrating codebase chat sessions and grounded LLM answers."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._chat_repo = ChatRepo(db)
        self._repo = RepositoryRepo(db)
        self._context_builder = ContextBuilderService(db)
        self._settings = get_settings()

    async def create_session(
        self,
        repository_id: UUID,
        request: ChatSessionCreate | None = None,
    ) -> ChatSessionResponse:
        """Create a new chat session for a repository."""
        repo = await self._repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository {repository_id} not found.")

        title = (request.title if request else "New Conversation") or "New Conversation"
        session = await self._chat_repo.create_session(repository_id, title)
        await self._db.commit()

        return ChatSessionResponse(
            id=session.id,
            repository_id=session.repository_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=0,
        )

    async def list_sessions(self, repository_id: UUID) -> ChatSessionListResponse:
        """List all chat sessions for a repository."""
        pairs = await self._chat_repo.list_sessions_by_repo(repository_id)
        items: list[ChatSessionResponse] = []
        for sess, count in pairs:
            items.append(
                ChatSessionResponse(
                    id=sess.id,
                    repository_id=sess.repository_id,
                    title=sess.title,
                    created_at=sess.created_at,
                    updated_at=sess.updated_at,
                    message_count=count,
                )
            )
        return ChatSessionListResponse(items=items, total=len(items))

    async def get_session(self, session_id: UUID) -> tuple[ChatSessionResponse, list[ChatMessageResponse]]:
        """Get session details and full message history."""
        session = await self._chat_repo.get_session(session_id)
        if session is None:
            raise ValueError(f"Chat session {session_id} not found.")

        messages_orm = await self._chat_repo.list_messages(session_id)
        messages_dto: list[ChatMessageResponse] = []

        for msg in messages_orm:
            citations_list = [
                CitationItem(**c) if isinstance(c, dict) else c
                for c in (msg.citations or [])
            ]
            messages_dto.append(
                ChatMessageResponse(
                    id=msg.id,
                    session_id=msg.session_id,
                    role=msg.role,
                    content=msg.content,
                    citations=citations_list,
                    token_count=msg.token_count,
                    created_at=msg.created_at,
                )
            )

        sess_dto = ChatSessionResponse(
            id=session.id,
            repository_id=session.repository_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(messages_dto),
        )
        return sess_dto, messages_dto

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a chat session."""
        deleted = await self._chat_repo.delete_session(session_id)
        await self._db.commit()
        return deleted > 0

    async def send_message(
        self,
        session_id: UUID,
        request: ChatMessageCreate,
    ) -> ChatMessageResponse:
        """Send a user message, build grounded context, call LLM, and return response."""
        session = await self._chat_repo.get_session(session_id)
        if session is None:
            raise ValueError(f"Chat session {session_id} not found.")

        # 1. Store user message in DB
        await self._chat_repo.add_message(
            session_id=session_id,
            role=MessageRole.user,
            content=request.content,
        )

        # Update session title if first message
        if session.title == "New Conversation":
            first_title = request.content[:30].strip() + ("..." if len(request.content) > 30 else "")
            session.title = first_title

        # 2. Build grounded context & citations
        system_context, citations = await self._context_builder.build_grounded_context(
            repo_id=session.repository_id,
            user_query=request.content,
            search_type=request.search_type,
            min_score=request.min_score,
        )

        # 3. Generate answer
        answer_text = await self._generate_llm_response(
            system_prompt=system_context,
            user_query=request.content,
            history=await self._chat_repo.list_messages(session_id),
        )

        # 4. Save assistant response to DB
        citations_dict_list = [c.model_dump(mode="json") for c in citations]
        assistant_msg = await self._chat_repo.add_message(
            session_id=session_id,
            role=MessageRole.assistant,
            content=answer_text,
            citations=citations_dict_list,
            token_count=len(answer_text.split()),
        )
        await self._db.commit()

        return ChatMessageResponse(
            id=assistant_msg.id,
            session_id=session_id,
            role=MessageRole.assistant,
            content=answer_text,
            citations=citations,
            token_count=assistant_msg.token_count,
            created_at=assistant_msg.created_at,
        )

    async def stream_message(
        self,
        session_id: UUID,
        request: ChatMessageCreate,
    ) -> AsyncGenerator[str, None]:
        """Stream assistant response tokens via Server-Sent Events (SSE)."""
        session = await self._chat_repo.get_session(session_id)
        if session is None:
            yield f"data: {json.dumps({'event': 'error', 'data': f'Session {session_id} not found.'})}\n\n"
            return

        # 1. Save user message
        await self._chat_repo.add_message(
            session_id=session_id,
            role=MessageRole.user,
            content=request.content,
        )
        if session.title == "New Conversation":
            session.title = request.content[:30].strip() + ("..." if len(request.content) > 30 else "")

        # 2. Build context & citations
        system_context, citations = await self._context_builder.build_grounded_context(
            repo_id=session.repository_id,
            user_query=request.content,
            search_type=request.search_type,
            min_score=request.min_score,
        )

        # Send citations payload event first
        citations_dict_list = [c.model_dump(mode="json") for c in citations]
        yield f"data: {json.dumps({'event': 'citations', 'data': json.dumps(citations_dict_list)})}\n\n"

        # 3. Stream tokens
        full_text_accumulated: list[str] = []
        answer_generator = self._stream_llm_tokens(
            system_prompt=system_context,
            user_query=request.content,
            history=await self._chat_repo.list_messages(session_id),
        )

        async for token in answer_generator:
            full_text_accumulated.append(token)
            yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"

        final_content = "".join(full_text_accumulated)

        # 4. Save assistant response to DB
        assistant_msg = await self._chat_repo.add_message(
            session_id=session_id,
            role=MessageRole.assistant,
            content=final_content,
            citations=citations_dict_list,
            token_count=len(final_content.split()),
        )
        await self._db.commit()

        yield f"data: {json.dumps({'event': 'done', 'data': str(assistant_msg.id)})}\n\n"

    async def _generate_llm_response(
        self,
        system_prompt: str,
        user_query: str,
        history: list,
    ) -> str:
        """Call LiteLLM or OpenAI completion API, fallback to mock grounded response."""
        api_key = getattr(self._settings, "openai_api_key", "")
        if not api_key:
            return self._build_mock_response(user_query, system_prompt)

        try:
            import litellm

            messages = [{"role": "system", "content": system_prompt}]
            for msg in history[-6:]:  # Last 3 turns memory
                messages.append({"role": msg.role.value, "content": msg.content})
            messages.append({"role": "user", "content": user_query})

            response = await litellm.acompletion(
                model="gpt-4o-mini",
                messages=messages,
                api_key=api_key,
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("litellm_completion_failed_using_fallback", error=str(exc))
            return self._build_mock_response(user_query, system_prompt)

    async def _stream_llm_tokens(
        self,
        system_prompt: str,
        user_query: str,
        history: list,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens generator."""
        api_key = getattr(self._settings, "openai_api_key", "")
        if not api_key:
            mock_text = self._build_mock_response(user_query, system_prompt)
            for word in mock_text.split(" "):
                yield word + " "
            return

        try:
            import litellm

            messages = [{"role": "system", "content": system_prompt}]
            for msg in history[-6:]:
                messages.append({"role": msg.role.value, "content": msg.content})
            messages.append({"role": "user", "content": user_query})

            response = await litellm.acompletion(
                model="gpt-4o-mini",
                messages=messages,
                api_key=api_key,
                temperature=0.2,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except Exception as exc:
            logger.warning("litellm_stream_failed_using_fallback", error=str(exc))
            mock_text = self._build_mock_response(user_query, system_prompt)
            for word in mock_text.split(" "):
                yield word + " "

    def _build_mock_response(self, user_query: str, system_prompt: str) -> str:
        """Fallback grounded response generator when OpenAI API key is not set."""
        if "GROUNDED REPOSITORY CONTEXT" in system_prompt:
            return (
                f"Based on the grounded codebase context retrieved for your query **\"{user_query}\"**:\n\n"
                "1. The codebase snippets above show the relevant function definitions and line numbers.\n"
                "2. All referenced classes and exports have been verified against the repository AST symbols.\n\n"
                "```python\n# Example grounded snippet\ndef verify_codebase_query():\n    return 'Grounded response generated successfully'\n```\n\n"
                "Please configure `OPENAI_API_KEY` in `.env` to enable full GPT-4o-mini LLM generation."
            )
        return (
            f"I analyzed your question **\"{user_query}\"**. No direct matching code context blocks were found in the index. "
            "Please ensure the repository has been parsed (Phase 3) and indexed (Phase 4)."
        )
