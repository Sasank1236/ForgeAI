"""ForgeAI services package.

Business logic services are added here incrementally:
  Phase 2: scanner.py, repository_service.py  ✓
  Phase 3: parser.py, tree_sitter_registry.py ✓
  Phase 4: embedding.py, chunker.py, knowledge_base.py ✓
  Phase 5: search.py                           ✓
  Phase 6: context_builder.py, chat_service.py ✓
  Phase 7: task_planner.py, code_suggestion.py ✓
  Phase 8: documentation.py
"""

# Phase 2
from forgeai.services.repository_service import RepositoryService
from forgeai.services.scanner import RepositoryScanner

# Phase 3
from forgeai.services.parser import ASTExtractor, CodeParserService
from forgeai.services.tree_sitter_registry import TreeSitterRegistry, registry

# Phase 4
from forgeai.services.chunker import CodeChunk, CodeChunker
from forgeai.services.embedding import EmbeddingService
from forgeai.services.knowledge_base import KnowledgeBaseService

# Phase 5
from forgeai.services.search import SearchService

# Phase 6
from forgeai.services.chat_service import ChatService
from forgeai.services.context_builder import ContextBuilderService

# Phase 7
from forgeai.services.code_suggestion import CodeSuggestionService
from forgeai.services.task_planner import TaskPlannerService

__all__ = [
    "RepositoryScanner",
    "RepositoryService",
    "TreeSitterRegistry",
    "registry",
    "CodeParserService",
    "ASTExtractor",
    "CodeChunk",
    "CodeChunker",
    "EmbeddingService",
    "KnowledgeBaseService",
    "SearchService",
    "ContextBuilderService",
    "ChatService",
    "TaskPlannerService",
    "CodeSuggestionService",
]
