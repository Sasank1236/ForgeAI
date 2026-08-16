"""Documentation ORM model.

Database table for storing auto-generated technical documentation
(README, Architecture guides, API reference, etc.).

Phase 8 — Auto Documentation Generation
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forgeai.database import Base


class DocType(enum.StrEnum):
    """Type of technical documentation."""

    readme = "readme"
    architecture = "architecture"
    api_reference = "api_reference"
    symbol_doc = "symbol_doc"


class DocStatus(enum.StrEnum):
    """Lifecycle status of generated documentation."""

    draft = "draft"
    generated = "generated"
    updated = "updated"


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class Documentation(Base):
    """ORM model representing generated repository technical documentation."""

    __tablename__ = "documentation"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    repository_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[DocType] = mapped_column(
        Enum(DocType, name="doc_type_enum", native_enum=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    status: Mapped[DocStatus] = mapped_column(
        Enum(DocStatus, name="doc_status_enum", native_enum=False),
        nullable=False,
        default=DocStatus.generated,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    repository: Mapped[object] = relationship(
        "Repository",
        back_populates="docs",
    )

    def __repr__(self) -> str:
        return f"<Documentation id={self.id} repo_id={self.repository_id} type={self.doc_type} title='{self.title}'>"
