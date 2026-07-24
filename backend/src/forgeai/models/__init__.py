"""ForgeAI models package.

ORM models are added here incrementally:
  Phase 2: repository.py, file.py  ✓
  Phase 3: symbol.py
  Phase 4: embedding.py
  Phase 6: conversation.py
  Phase 9: documentation.py

Importing this package is sufficient for Alembic autogenerate and
SQLAlchemy relationship resolution — all models register themselves
against ``Base.metadata`` on import.
"""

# Phase 2
from forgeai.models.repository import Repository, RepositoryStatus
from forgeai.models.file import RepositoryFile

__all__ = [
    "Repository",
    "RepositoryStatus",
    "RepositoryFile",
]
