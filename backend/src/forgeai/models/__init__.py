"""ForgeAI models package.

ORM models are added here incrementally:
  Phase 2: repository.py, file.py  ✓
  Phase 3: symbol.py, import_.py   ✓
  Phase 4: embedding.py            ✓
  Phase 6: chat.py                 ✓
  Phase 7: plan.py                 ✓
  Phase 8: documentation.py        ✓
"""

from forgeai.models.chat import ChatMessage, ChatSession, MessageRole
from forgeai.models.documentation import DocStatus, DocType, Documentation
from forgeai.models.embedding import ChunkType, CodeEmbedding
from forgeai.models.file import RepositoryFile
from forgeai.models.import_ import Import, ImportType
from forgeai.models.plan import PlanStatus, PlanStep, TaskPlan
from forgeai.models.repository import Repository, RepositoryStatus
from forgeai.models.symbol import Symbol, SymbolType, Visibility

__all__ = [
    "ChatMessage",
    "ChatSession",
    "ChunkType",
    "CodeEmbedding",
    "DocStatus",
    "DocType",
    "Documentation",
    "Import",
    "ImportType",
    "MessageRole",
    "PlanStatus",
    "PlanStep",
    "Repository",
    "RepositoryFile",
    "RepositoryStatus",
    "Symbol",
    "SymbolType",
    "TaskPlan",
    "Visibility",
]
