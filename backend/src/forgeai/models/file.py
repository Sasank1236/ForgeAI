"""RepositoryFile ORM model.

Represents a single file discovered during a repository scan.
Includes metadata for language detection, binary detection, and
Phase 3 parsing placeholders (parsed, symbols_count).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forgeai.database import Base


class RepositoryFile(Base):
    """Represents a single file within an imported repository.

    Columns
    -------
    id              UUID primary key.
    repository_id   FK → repositories.id (CASCADE DELETE).
    relative_path   Path relative to the repository root (unique per repo).
    absolute_path   Full filesystem path at scan time.
    language        Human-readable language name (e.g. "Python"), or None.
    extension       File extension including dot (e.g. ".py").
    size            File size in bytes.
    sha256          SHA-256 hex digest; used to detect unchanged files.
    last_modified   File mtime as a UTC-aware datetime.
    is_binary       True when the file contains non-text content.
    mime_type       MIME type guessed from extension (e.g. "text/x-python").
    line_count      Number of lines; 0 for binary or empty files.

    Phase 3 placeholders (schema-ready, populated by the parser):
    parsed          Whether tree-sitter has processed this file.
    symbols_count   Number of symbols extracted by tree-sitter.
    """

    __tablename__ = "repository_files"

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

    # ── Path information ──────────────────────────────────────────────────────
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    absolute_path: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Language & type ───────────────────────────────────────────────────────
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extension: Mapped[str] = mapped_column(
        String(50), nullable=False, default="", server_default=""
    )
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_binary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # ── Size & content metrics ────────────────────────────────────────────────
    size: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    line_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ── Phase 3 parsing placeholders ─────────────────────────────────────────
    parsed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    symbols_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ── Constraints ───────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "relative_path",
            name="uq_repo_file_path",
        ),
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    repository: Mapped[Repository] = relationship(  # type: ignore[name-defined]
        "Repository", back_populates="files"
    )

    def __repr__(self) -> str:
        return (
            f"<RepositoryFile id={self.id} "
            f"path={self.relative_path!r} lang={self.language!r}>"
        )


# Resolve the forward reference
from forgeai.models.repository import Repository  # noqa: E402, F401
