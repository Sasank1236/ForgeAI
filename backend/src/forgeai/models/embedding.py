"""CodeEmbedding ORM model.

Represents a vector embedding chunk extracted from a repository file or symbol.

Phase 4 — Vector Embeddings & Knowledge Base
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forgeai.database import Base

if TYPE_CHECKING:
    from forgeai.models.file import RepositoryFile
    from forgeai.models.repository import Repository
    from forgeai.models.symbol import Symbol


class ChunkType(enum.StrEnum):
    """Kinds of code chunks generated for vector embedding."""

    symbol = "symbol"
    file_header = "file_header"
    window = "window"


class CodeEmbedding(Base):
    """Represents a code chunk vector embedding.

    Columns
    -------
    id              UUID primary key, auto-generated.
    repository_id   FK -> repositories.id (CASCADE DELETE).
    file_id         FK -> repository_files.id (CASCADE DELETE).
    symbol_id       Optional FK -> symbols.id (CASCADE DELETE).
    chunk_index     0-based chunk sequence index within the file.
    chunk_text      Raw text content of the chunk.
    token_count     Estimated token length of chunk_text.
    chunk_type      Kind of chunk (see ChunkType enum).
    start_line      1-based start line number.
    end_line        1-based end line number.
    embedding       1536-dimensional vector (pgvector).
    created_at      Timestamp when chunk embedding was generated.
    """

    __tablename__ = "code_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    chunk_type: Mapped[ChunkType] = mapped_column(
        SAEnum(ChunkType, name="chunk_type"),
        nullable=False,
        default=ChunkType.window,
    )

    start_line: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 1536-dimensional vector for OpenAI text-embedding-3-small
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    repository: Mapped[Repository] = relationship("Repository", lazy="select")
    file: Mapped[RepositoryFile] = relationship("RepositoryFile", lazy="select")
    symbol: Mapped[Symbol | None] = relationship("Symbol", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<CodeEmbedding id={self.id} file_id={self.file_id} "
            f"chunk_index={self.chunk_index} type={self.chunk_type}>"
        )
