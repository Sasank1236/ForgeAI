"""Tree-sitter language registry and parser loader.

Loads and caches Tree-sitter Language bindings and Parser instances.
Maps file extensions and language names to tree-sitter parsers.

Supported Languages out-of-the-box:
  - Python (.py, .pyi)
  - JavaScript (.js, .jsx, .mjs, .cjs)
  - TypeScript (.ts)
  - TSX (.tsx)
  - Go (.go)
  - Java (.java)
  - C++ (.cpp, .cxx, .cc, .hpp, .h)
  - Rust (.rs)

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

import structlog
import tree_sitter
from tree_sitter import Language, Parser

logger = structlog.get_logger(__name__)


class TreeSitterRegistry:
    """Registry for managing Tree-sitter language grammars and parsers."""

    def __init__(self) -> None:
        self._languages: dict[str, Language] = {}
        self._ext_map: dict[str, str] = {}
        self._canonical_names: dict[str, str] = {}

        self._load_default_grammars()

    def _load_default_grammars(self) -> None:
        """Attempt to load built-in language bindings."""
        # Python
        try:
            import tree_sitter_python

            self.register_language(
                name="python",
                canonical_name="Python",
                language=Language(tree_sitter_python.language()),
                extensions=[".py", ".pyi", ".pyx"],
            )
        except Exception as err:
            logger.warning("failed_to_load_grammar", language="python", error=str(err))

        # JavaScript
        try:
            import tree_sitter_javascript

            self.register_language(
                name="javascript",
                canonical_name="JavaScript",
                language=Language(tree_sitter_javascript.language()),
                extensions=[".js", ".jsx", ".mjs", ".cjs"],
            )
        except Exception as err:
            logger.warning("failed_to_load_grammar", language="javascript", error=str(err))

        # TypeScript
        try:
            import tree_sitter_typescript

            self.register_language(
                name="typescript",
                canonical_name="TypeScript",
                language=Language(tree_sitter_typescript.language_typescript()),
                extensions=[".ts"],
            )
            # TSX is part of tree_sitter_typescript package
            self.register_language(
                name="tsx",
                canonical_name="TSX",
                language=Language(tree_sitter_typescript.language_tsx()),
                extensions=[".tsx"],
            )
        except Exception as err:
            logger.warning("failed_to_load_grammar", language="typescript", error=str(err))

        # Go
        try:
            import tree_sitter_go

            self.register_language(
                name="go",
                canonical_name="Go",
                language=Language(tree_sitter_go.language()),
                extensions=[".go"],
            )
        except Exception as err:
            logger.warning("failed_to_load_grammar", language="go", error=str(err))

        # Java
        try:
            import tree_sitter_java

            self.register_language(
                name="java",
                canonical_name="Java",
                language=Language(tree_sitter_java.language()),
                extensions=[".java"],
            )
        except Exception as err:
            logger.warning("failed_to_load_grammar", language="java", error=str(err))

        # C++
        try:
            import tree_sitter_cpp

            self.register_language(
                name="cpp",
                canonical_name="C++",
                language=Language(tree_sitter_cpp.language()),
                extensions=[".cpp", ".cxx", ".cc", ".hpp", ".h"],
            )
        except Exception as err:
            logger.warning("failed_to_load_grammar", language="cpp", error=str(err))

        # Rust
        try:
            import tree_sitter_rust

            self.register_language(
                name="rust",
                canonical_name="Rust",
                language=Language(tree_sitter_rust.language()),
                extensions=[".rs"],
            )
        except Exception as err:
            logger.warning("failed_to_load_grammar", language="rust", error=str(err))

        logger.info(
            "tree_sitter_registry_initialized",
            supported_languages=list(self._languages.keys()),
            extensions_mapped=len(self._ext_map),
        )

    def register_language(
        self,
        name: str,
        canonical_name: str,
        language: Language,
        extensions: list[str],
    ) -> None:
        """Register a new language grammar and its associated extensions.

        Parameters
        ----------
        name:
            Lower-case internal key (e.g. "python", "typescript").
        canonical_name:
            Human-readable display name (e.g. "Python", "TypeScript").
        language:
            Loaded ``tree_sitter.Language`` instance.
        extensions:
            File extensions associated with this language (e.g. [".py", ".pyi"]).
        """
        key = name.lower()
        self._languages[key] = language
        self._canonical_names[key] = canonical_name

        for ext in extensions:
            ext_normalized = ext.lower()
            if not ext_normalized.startswith("."):
                ext_normalized = f".{ext_normalized}"
            self._ext_map[ext_normalized] = key

    def get_language(self, lang_or_ext: str) -> Language | None:
        """Lookup ``tree_sitter.Language`` by extension or language name."""
        target = lang_or_ext.lower().strip()
        if target.startswith("."):
            lang_key = self._ext_map.get(target)
            if lang_key:
                return self._languages.get(lang_key)
            return None

        # Check by language key directly
        if target in self._languages:
            return self._languages[target]

        # Check by extension lookup if dot was omitted (e.g. "py")
        lang_key = self._ext_map.get(f".{target}")
        if lang_key:
            return self._languages.get(lang_key)

        return None

    def get_parser(self, lang_or_ext: str) -> Parser | None:
        """Return a configured ``tree_sitter.Parser`` for the given extension or language."""
        lang = self.get_language(lang_or_ext)
        if lang is None:
            return None
        return Parser(lang)

    def get_canonical_name(self, lang_or_ext: str) -> str | None:
        """Return human-readable language display name (e.g. "Python", "TypeScript")."""
        target = lang_or_ext.lower().strip()
        if target.startswith("."):
            lang_key = self._ext_map.get(target)
            if lang_key:
                return self._canonical_names.get(lang_key)
            return None

        if target in self._canonical_names:
            return self._canonical_names[target]

        lang_key = self._ext_map.get(f".{target}")
        if lang_key:
            return self._canonical_names.get(lang_key)

        return None

    def parse_code(
        self,
        code: str | bytes,
        lang_or_ext: str,
    ) -> tree_sitter.Tree | None:
        """Parse source code string or bytes into a Tree-sitter AST Tree.

        Returns None if language is unsupported or parsing fails completely.
        """
        parser = self.get_parser(lang_or_ext)
        if parser is None:
            return None

        code_bytes = code.encode("utf-8") if isinstance(code, str) else code
        try:
            return parser.parse(code_bytes)
        except Exception as err:
            logger.error("parse_code_failed", lang_or_ext=lang_or_ext, error=str(err))
            return None

    def is_supported(self, lang_or_ext: str) -> bool:
        """Check if a file extension or language is supported by the registry."""
        return self.get_language(lang_or_ext) is not None


# Global singleton instance for easy import across services
registry = TreeSitterRegistry()
