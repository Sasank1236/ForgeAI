"""Symbol ORM model.

Represents a code symbol (function, class, method, etc.) extracted from
a repository file via Tree-sitter AST parsing.

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forgeai.database import Base

if TYPE_CHECKING:
    from forgeai.models.file import RepositoryFile
    from forgeai.models.repository import Repository


# ── Enums ─────────────────────────────────────────────────────────────────────

class SymbolType(enum.StrEnum):
    """Kinds of code symbols that the parser can extract."""

    function = "function"
    class_ = "class"
    method = "method"
    constructor = "constructor"
    interface = "interface"
    enum_ = "enum"
    struct = "struct"
    variable = "variable"
    constant = "constant"
    type_alias = "type_alias"
    module = "module"
    namespace = "namespace"


class Visibility(enum.StrEnum):
    """Access visibility modifiers."""

    public = "public"
    private = "private"
    protected = "protected"
    internal = "internal"


# ── Model ─────────────────────────────────────────────────────────────────────

class Symbol(Base):
    """Represents a code symbol extracted from a source file.

    Columns
    -------
    id              UUID primary key, auto-generated.
    repository_id   FK -> repositories.id (CASCADE DELETE).
    file_id         FK -> repository_files.id (CASCADE DELETE).
    name            Symbol name (e.g. ``my_function``).
    symbol_type     Kind of symbol (see SymbolType enum).
    language        Language the symbol was parsed from (e.g. "Python").
    parent_symbol_id Optional FK -> symbols.id for nested symbols
                     (e.g. a method inside a class).
    start_line      1-based line where the symbol definition starts.
    end_line        1-based line where the symbol definition ends.
    start_column    0-based column where the symbol starts.
    end_column      0-based column where the symbol ends.
    visibility      Access modifier (public/private/protected/internal).
    signature       Full declaration signature (e.g. ``def foo(x: int) -> str``).
    docstring       Documentation string extracted from the symbol body.
    """

    __tablename__ = "symbols"

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

    name: Mapped[str] = mapped_column(String(500), nullable=False)

    symbol_type: Mapped[SymbolType] = mapped_column(
        SAEnum(SymbolType, name="symbol_type"),
        nullable=False,
    )

    language: Mapped[str] = mapped_column(String(100), nullable=False)

    # Self-referential FK for parent symbol (class -> method, namespace -> class)
    parent_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ── Position ──────────────────────────────────────────────────────────────
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    start_column: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    end_column: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    visibility: Mapped[Visibility | None] = mapped_column(
        SAEnum(Visibility, name="symbol_visibility"),
        nullable=True,
    )
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    repository: Mapped[Repository] = relationship(
        "Repository",
        lazy="select",
    )
    file: Mapped[RepositoryFile] = relationship(
        "RepositoryFile",
        lazy="select",
    )
    parent: Mapped[Symbol | None] = relationship(
        "Symbol",
        remote_side="Symbol.id",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Symbol id={self.id} name={self.name!r} "
            f"type={self.symbol_type} lang={self.language!r}>"
        )
