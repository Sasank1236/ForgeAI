"""Import ORM model.

Represents an import/dependency statement extracted from a repository file
via Tree-sitter AST parsing.

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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forgeai.database import Base

if TYPE_CHECKING:
    from forgeai.models.file import RepositoryFile
    from forgeai.models.repository import Repository


# ── Enum ──────────────────────────────────────────────────────────────────────

class ImportType(enum.StrEnum):
    """Kinds of import statements across supported languages."""

    import_ = "import"                  # Python: import os
    from_import = "from_import"         # Python: from os import path
    require = "require"                 # JS: const x = require('x')
    dynamic_import = "dynamic_import"   # JS: import('x')
    include = "include"                 # C++: #include <stdio.h>
    package = "package"                 # Java: package com.example
    export = "export"                   # JS/TS: export { foo }
    re_export = "re_export"             # JS/TS: export { foo } from './bar'
    side_effect = "side_effect"         # JS: import './styles.css'


# ── Model ─────────────────────────────────────────────────────────────────────

class Import(Base):
    """Represents an import or dependency statement in a source file.

    Columns
    -------
    id              UUID primary key, auto-generated.
    repository_id   FK -> repositories.id (CASCADE DELETE).
    file_id         FK -> repository_files.id (CASCADE DELETE).
    source_symbol   The imported name or symbol (e.g. ``path``, ``useState``).
    target_module   The module being imported from (e.g. ``os``, ``react``).
    import_type     The kind of import (see ImportType enum).
    alias           Optional alias (e.g. ``import numpy as np`` -> alias="np").
    """

    __tablename__ = "imports"

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

    source_symbol: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    target_module: Mapped[str] = mapped_column(Text, nullable=False)

    import_type: Mapped[ImportType] = mapped_column(
        SAEnum(ImportType, name="import_type"),
        nullable=False,
    )

    alias: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    repository: Mapped[Repository] = relationship(
        "Repository",
        lazy="select",
    )
    file: Mapped[RepositoryFile] = relationship(
        "RepositoryFile",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Import id={self.id} "
            f"module={self.target_module!r} symbol={self.source_symbol!r} "
            f"type={self.import_type}>"
        )
