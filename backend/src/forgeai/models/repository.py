"""Repository ORM model.

Represents an imported local repository with its scan metadata,
Git information, and scan versioning for incremental re-indexing support.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from forgeai.database import Base


class RepositoryStatus(str, enum.Enum):
    """Lifecycle states of a repository import."""

    pending = "pending"  # Created, not yet scanned
    scanning = "scanning"  # Scan in progress
    ready = "ready"  # Scan complete, data available
    error = "error"  # Scan failed


class Repository(Base):
    """Represents an imported local repository.

    Columns
    -------
    id              UUID primary key, auto-generated.
    name            Derived from the root directory name.
    root_path       Absolute path on the local filesystem (unique).
    status          Current lifecycle state (see RepositoryStatus).
    scan_version    Increments on every rescan; useful for
                    incremental indexing and embedding regeneration.
    default_branch  Git HEAD branch name (optional).
    current_commit  Full SHA of HEAD commit (optional).
    git_remote      URL of the origin remote (optional).
    created_at      UTC timestamp of first import.
    last_scanned    UTC timestamp of most recent successful scan.
    files           One-to-many relationship to RepositoryFile rows.
    """

    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    status: Mapped[RepositoryStatus] = mapped_column(
        SAEnum(RepositoryStatus, name="repository_status"),
        nullable=False,
        default=RepositoryStatus.pending,
        server_default=RepositoryStatus.pending.value,
    )

    # Incremented on every rescan
    scan_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # ── Git information (all optional) ────────────────────────────────────────
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    git_remote: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_scanned: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    files: Mapped[list[RepositoryFile]] = relationship(  # type: ignore[name-defined]
        "RepositoryFile",
        back_populates="repository",
        cascade="all, delete-orphan",
        lazy="select",
    )
    docs: Mapped[list] = relationship(
        "Documentation",
        back_populates="repository",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Repository id={self.id} name={self.name!r} status={self.status}>"


# Resolve the forward reference used in the relationship above
from forgeai.models.file import RepositoryFile  # noqa: E402, F401
