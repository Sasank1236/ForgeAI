"""Tree-sitter source code parser service.

Parses source code using Tree-sitter AST nodes to extract:
  - Code Symbols (functions, classes, methods, constructors, interfaces,
    structs, enums, type aliases, variables, modules, namespaces) with
    position, visibility, signature, docstring, and hierarchy relationships.
  - Imports & Dependencies (imports, from-imports, requires, includes,
    packages, exports, re-exports, side-effects).

Orchestrates database persistence via SymbolRepo and ImportRepo.

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from tree_sitter import Node

from forgeai.models.file import RepositoryFile
from forgeai.models.import_ import ImportType
from forgeai.models.repository import RepositoryStatus
from forgeai.models.symbol import SymbolType, Visibility
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.import_repo import ImportRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.repositories.symbol_repo import SymbolRepo
from forgeai.schemas.parser import (
    LanguageParseStats,
    ParseRequest,
    ParseResponse,
    ParseStatsResponse,
)
from forgeai.services.tree_sitter_registry import TreeSitterRegistry, registry

logger = structlog.get_logger(__name__)


@dataclass
class ExtractedSymbol:
    """Intermediate representation of an extracted symbol before DB insertion."""

    name: str
    symbol_type: SymbolType
    start_line: int  # 1-based
    end_line: int  # 1-based
    start_column: int = 0  # 0-based
    end_column: int = 0  # 0-based
    visibility: Visibility | None = None
    signature: str | None = None
    docstring: str | None = None
    parent_index: int | None = None  # Index in extracted list for hierarchy


@dataclass
class ExtractedImport:
    """Intermediate representation of an extracted import before DB insertion."""

    target_module: str
    import_type: ImportType
    source_symbol: str | None = None
    alias: str | None = None


@dataclass
class ParseResult:
    """Extracted symbols and imports from a single file."""

    symbols: list[ExtractedSymbol] = field(default_factory=list)
    imports: list[ExtractedImport] = field(default_factory=list)


# ── AST Extractor ─────────────────────────────────────────────────────────────


class ASTExtractor:
    """Language-agnostic + per-language AST extractor using Tree-sitter."""

    def __init__(self, registry_instance: TreeSitterRegistry = registry) -> None:
        self._registry = registry_instance

    def extract(self, code: str, lang_or_ext: str) -> ParseResult:
        """Parse source code string and extract symbols and imports."""
        tree = self._registry.parse_code(code, lang_or_ext)
        if tree is None:
            return ParseResult()

        canonical = self._registry.get_canonical_name(lang_or_ext) or ""
        lang_key = canonical.lower()

        code_bytes = code.encode("utf-8")
        result = ParseResult()

        root = tree.root_node
        if lang_key == "python":
            self._extract_python(root, code_bytes, result)
        elif lang_key in ("javascript", "typescript", "tsx"):
            self._extract_js_ts(root, code_bytes, result)
        elif lang_key == "go":
            self._extract_go(root, code_bytes, result)
        elif lang_key == "java":
            self._extract_java(root, code_bytes, result)
        elif lang_key == "c++":
            self._extract_cpp(root, code_bytes, result)
        elif lang_key == "rust":
            self._extract_rust(root, code_bytes, result)
        else:
            self._extract_generic(root, code_bytes, result)

        return result

    # ── Python Extractor ──────────────────────────────────────────────────────

    def _extract_python(
        self,
        node: Node,
        code_bytes: bytes,
        res: ParseResult,
        parent_idx: int | None = None,
    ) -> None:
        for child in node.children:
            ntype = child.type
            if ntype in ("function_definition", "async_function_definition"):
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                stype = (
                    SymbolType.method if parent_idx is not None else SymbolType.function
                )

                # Visibility
                vis = Visibility.private if name.startswith("_") else Visibility.public

                # Signature
                sig = self._first_line(child, code_bytes)

                # Docstring
                doc = self._python_docstring(child, code_bytes)

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        visibility=vis,
                        signature=sig,
                        docstring=doc,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_python(body, code_bytes, res, parent_idx=idx)

            elif ntype == "class_definition":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                vis = Visibility.private if name.startswith("_") else Visibility.public
                sig = self._first_line(child, code_bytes)
                doc = self._python_docstring(child, code_bytes)

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.class_,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        visibility=vis,
                        signature=sig,
                        docstring=doc,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_python(body, code_bytes, res, parent_idx=idx)

            elif ntype == "import_statement":
                for sub in child.children:
                    if sub.type in ("dotted_name", "aliased_import"):
                        if sub.type == "aliased_import":
                            name_n = sub.child_by_field_name("name")
                            alias_n = sub.child_by_field_name("alias")
                            mod = self._node_text(name_n, code_bytes)
                            alias = self._node_text(alias_n, code_bytes)
                        else:
                            mod = self._node_text(sub, code_bytes)
                            alias = None
                        if mod:
                            res.imports.append(
                                ExtractedImport(
                                    target_module=mod,
                                    import_type=ImportType.import_,
                                    alias=alias,
                                )
                            )

            elif ntype == "import_from_statement":
                module_node = child.child_by_field_name("module_name")
                mod_name = (
                    self._node_text(module_node, code_bytes) if module_node else ""
                )
                # Get names imported
                for sub in child.children:
                    if sub.type in ("dotted_name", "aliased_import", "import_list"):
                        if sub.type == "import_list":
                            for item in sub.children:
                                self._process_py_import_item(
                                    item, mod_name, code_bytes, res
                                )
                        elif sub != module_node:
                            self._process_py_import_item(sub, mod_name, code_bytes, res)

    def _process_py_import_item(
        self, node: Node, mod_name: str, code_bytes: bytes, res: ParseResult
    ) -> None:
        if node.type == "aliased_import":
            name_n = node.child_by_field_name("name")
            alias_n = node.child_by_field_name("alias")
            src = self._node_text(name_n, code_bytes)
            alias = self._node_text(alias_n, code_bytes)
            if src:
                res.imports.append(
                    ExtractedImport(
                        target_module=mod_name or src,
                        source_symbol=src,
                        import_type=ImportType.from_import,
                        alias=alias,
                    )
                )
        elif node.type in ("dotted_name", "identifier"):
            src = self._node_text(node, code_bytes)
            if src:
                res.imports.append(
                    ExtractedImport(
                        target_module=mod_name or src,
                        source_symbol=src if mod_name else None,
                        import_type=ImportType.from_import
                        if mod_name
                        else ImportType.import_,
                    )
                )

    def _python_docstring(self, node: Node, code_bytes: bytes) -> str | None:
        body = node.child_by_field_name("body")
        if not body or not body.children:
            return None
        first = body.children[0]
        if first.type == "expression_statement" and first.children:
            expr = first.children[0]
            if expr.type == "string":
                text = self._node_text(expr, code_bytes)
                return text.strip("\"' \t\r\n")
        return None

    # ── JavaScript / TypeScript Extractor ────────────────────────────────────

    def _extract_js_ts(
        self,
        node: Node,
        code_bytes: bytes,
        res: ParseResult,
        parent_idx: int | None = None,
    ) -> None:
        for child in node.children:
            ntype = child.type
            if ntype in (
                "function_declaration",
                "generator_function_declaration",
                "method_definition",
            ):
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                stype = (
                    SymbolType.method if parent_idx is not None else SymbolType.function
                )
                sig = self._first_line(child, code_bytes)

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_js_ts(body, code_bytes, res, parent_idx=idx)

            elif ntype == "class_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                sig = self._first_line(child, code_bytes)

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.class_,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_js_ts(body, code_bytes, res, parent_idx=idx)

            elif ntype == "interface_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.interface,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "enum_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.enum_,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "type_alias_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.type_alias,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "import_statement":
                source_node = child.child_by_field_name("source")
                mod = (
                    self._node_text(source_node, code_bytes).strip("'\"")
                    if source_node
                    else ""
                )
                if mod:
                    # Look for import clause
                    import_clause = child.child_by_field_name("import_clause")
                    if import_clause:
                        text = self._node_text(import_clause, code_bytes)
                        res.imports.append(
                            ExtractedImport(
                                target_module=mod,
                                source_symbol=text,
                                import_type=ImportType.from_import,
                            )
                        )
                    else:
                        res.imports.append(
                            ExtractedImport(
                                target_module=mod,
                                import_type=ImportType.side_effect
                                if not import_clause
                                else ImportType.import_,
                            )
                        )

            elif ntype == "export_statement":
                # Check for export ... from '...'
                source_node = child.child_by_field_name("source")
                if source_node:
                    mod = self._node_text(source_node, code_bytes).strip("'\"")
                    res.imports.append(
                        ExtractedImport(
                            target_module=mod,
                            import_type=ImportType.re_export,
                        )
                    )
                else:
                    self._extract_js_ts(child, code_bytes, res, parent_idx)

            elif child.children:
                self._extract_js_ts(child, code_bytes, res, parent_idx)

    # ── Go Extractor ──────────────────────────────────────────────────────────

    def _extract_go(
        self,
        node: Node,
        code_bytes: bytes,
        res: ParseResult,
        parent_idx: int | None = None,
    ) -> None:
        for child in node.children:
            ntype = child.type
            if ntype == "function_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                vis = (
                    Visibility.public
                    if name and name[0].isupper()
                    else Visibility.private
                )
                sig = self._first_line(child, code_bytes)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.function,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        visibility=vis,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "method_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                vis = (
                    Visibility.public
                    if name and name[0].isupper()
                    else Visibility.private
                )
                sig = self._first_line(child, code_bytes)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.method,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        visibility=vis,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "type_spec":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                type_node = child.child_by_field_name("type")
                stype = SymbolType.struct
                if type_node and type_node.type == "interface_type":
                    stype = SymbolType.interface
                elif type_node and type_node.type == "struct_type":
                    stype = SymbolType.struct

                vis = (
                    Visibility.public
                    if name and name[0].isupper()
                    else Visibility.private
                )
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        visibility=vis,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "import_spec":
                path_node = child.child_by_field_name("path")
                mod = (
                    self._node_text(path_node, code_bytes).strip('"`')
                    if path_node
                    else ""
                )
                alias_node = child.child_by_field_name("name")
                alias = self._node_text(alias_node, code_bytes) if alias_node else None
                if mod:
                    res.imports.append(
                        ExtractedImport(
                            target_module=mod,
                            import_type=ImportType.import_,
                            alias=alias,
                        )
                    )

            elif child.children:
                self._extract_go(child, code_bytes, res, parent_idx)

    # ── Java Extractor ────────────────────────────────────────────────────────

    def _extract_java(
        self,
        node: Node,
        code_bytes: bytes,
        res: ParseResult,
        parent_idx: int | None = None,
    ) -> None:
        for child in node.children:
            ntype = child.type
            if ntype in (
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
            ):
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                stype = (
                    SymbolType.class_
                    if ntype == "class_declaration"
                    else (
                        SymbolType.interface
                        if ntype == "interface_declaration"
                        else SymbolType.enum_
                    )
                )
                sig = self._first_line(child, code_bytes)

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_java(body, code_bytes, res, parent_idx=idx)

            elif ntype == "method_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                sig = self._first_line(child, code_bytes)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.method,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "constructor_declaration":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                sig = self._first_line(child, code_bytes)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.constructor,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )

            elif ntype == "package_declaration":
                pkg_text = (
                    self._node_text(child, code_bytes)
                    .replace("package", "")
                    .strip("; ")
                )
                if pkg_text:
                    res.imports.append(
                        ExtractedImport(
                            target_module=pkg_text,
                            import_type=ImportType.package,
                        )
                    )

            elif ntype == "import_declaration":
                imp_text = (
                    self._node_text(child, code_bytes).replace("import", "").strip("; ")
                )
                if imp_text:
                    res.imports.append(
                        ExtractedImport(
                            target_module=imp_text,
                            import_type=ImportType.import_,
                        )
                    )

            elif child.children:
                self._extract_java(child, code_bytes, res, parent_idx)

    # ── C++ Extractor ─────────────────────────────────────────────────────────

    def _extract_cpp(
        self,
        node: Node,
        code_bytes: bytes,
        res: ParseResult,
        parent_idx: int | None = None,
    ) -> None:
        for child in node.children:
            ntype = child.type
            if ntype in ("function_definition", "function_declarator"):
                decl = child.child_by_field_name("declarator") or child
                name = self._node_text(decl, code_bytes)
                if "(" in name:
                    name = name.split("(")[0].strip()
                if not name:
                    name = "anonymous"

                sig = self._first_line(child, code_bytes)
                stype = (
                    SymbolType.method if parent_idx is not None else SymbolType.function
                )

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_cpp(body, code_bytes, res, parent_idx=idx)

            elif ntype in ("class_specifier", "struct_specifier"):
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                stype = (
                    SymbolType.class_
                    if ntype == "class_specifier"
                    else SymbolType.struct
                )
                sig = self._first_line(child, code_bytes)

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_cpp(body, code_bytes, res, parent_idx=idx)

            elif ntype == "namespace_definition":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.namespace,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_cpp(body, code_bytes, res, parent_idx=idx)

            elif ntype == "preproc_include":
                path_node = child.child_by_field_name("path")
                header = (
                    self._node_text(path_node, code_bytes).strip("<\"'>")
                    if path_node
                    else ""
                )
                if header:
                    res.imports.append(
                        ExtractedImport(
                            target_module=header,
                            import_type=ImportType.include,
                        )
                    )

            elif child.children:
                self._extract_cpp(child, code_bytes, res, parent_idx)

    # ── Rust Extractor ────────────────────────────────────────────────────────

    def _extract_rust(
        self,
        node: Node,
        code_bytes: bytes,
        res: ParseResult,
        parent_idx: int | None = None,
    ) -> None:
        for child in node.children:
            ntype = child.type
            if ntype == "function_item":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                sig = self._first_line(child, code_bytes)
                stype = (
                    SymbolType.method if parent_idx is not None else SymbolType.function
                )

                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )

            elif ntype in ("struct_item", "enum_item", "trait_item"):
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )
                stype = (
                    SymbolType.struct
                    if ntype == "struct_item"
                    else (
                        SymbolType.enum_
                        if ntype == "enum_item"
                        else SymbolType.interface
                    )
                )
                sig = self._first_line(child, code_bytes)

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=stype,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=sig,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_rust(body, code_bytes, res, parent_idx=idx)

            elif ntype == "impl_item":
                body = child.child_by_field_name("body")
                if body:
                    self._extract_rust(body, code_bytes, res, parent_idx)

            elif ntype == "mod_item":
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else "anonymous"
                )

                idx = len(res.symbols)
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.module,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        parent_index=parent_idx,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    self._extract_rust(body, code_bytes, res, parent_idx=idx)

            elif ntype == "use_declaration":
                text = self._node_text(child, code_bytes).replace("use", "").strip("; ")
                if text:
                    res.imports.append(
                        ExtractedImport(
                            target_module=text,
                            import_type=ImportType.import_,
                        )
                    )

            elif child.children:
                self._extract_rust(child, code_bytes, res, parent_idx)

    # ── Generic Fallback ──────────────────────────────────────────────────────

    def _extract_generic(
        self,
        node: Node,
        code_bytes: bytes,
        res: ParseResult,
        parent_idx: int | None = None,
    ) -> None:
        for child in node.children:
            if "function" in child.type or "method" in child.type:
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else child.type
                )
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.function,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        parent_index=parent_idx,
                    )
                )
            elif "class" in child.type or "struct" in child.type:
                name_node = child.child_by_field_name("name")
                name = (
                    self._node_text(name_node, code_bytes) if name_node else child.type
                )
                res.symbols.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.class_,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        parent_index=parent_idx,
                    )
                )
            elif child.children:
                self._extract_generic(child, code_bytes, res, parent_idx)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _node_text(self, node: Node | None, code_bytes: bytes) -> str:
        if node is None:
            return ""
        return code_bytes[node.start_byte : node.end_byte].decode(
            "utf-8", errors="replace"
        )

    def _first_line(self, node: Node, code_bytes: bytes) -> str:
        full = self._node_text(node, code_bytes)
        first = full.splitlines()[0] if full else ""
        return first[:500]


# ── CodeParserService ─────────────────────────────────────────────────────────


class CodeParserService:
    """Service layer orchestrating AST parsing and DB persistence."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo_repo = RepositoryRepo(db)
        self._file_repo = FileRepo(db)
        self._symbol_repo = SymbolRepo(db)
        self._import_repo = ImportRepo(db)
        self._extractor = ASTExtractor()

    async def parse_repository(
        self, repo_id: UUID, req: ParseRequest | None = None
    ) -> ParseResponse:
        """Parse all eligible source files in a repository and persist symbols/imports."""
        start_time = asyncio.get_event_loop().time()
        req = req or ParseRequest()

        repo = await self._repo_repo.get_by_id(repo_id)
        if repo is None:
            raise ValueError(f"Repository {repo_id} not found.")

        # Update status to scanning
        await self._repo_repo.update_status(repo_id, RepositoryStatus.scanning)
        await self._db.commit()

        # Fetch files to process
        page = 1
        all_files: list[RepositoryFile] = []
        while True:
            files, total = await self._file_repo.list_by_repo(
                repo_id, page=page, page_size=200
            )
            if not files:
                break
            all_files.extend(files)
            if len(all_files) >= total:
                break
            page += 1

        # Apply request filters
        if req.file_ids:
            target_ids = set(req.file_ids)
            all_files = [f for f in all_files if f.id in target_ids]

        if req.languages:
            target_langs = {l.lower() for l in req.languages}
            all_files = [
                f
                for f in all_files
                if f.language and f.language.lower() in target_langs
            ]

        by_lang_stats: dict[str, LanguageParseStats] = {}
        total_parsed = 0
        total_skipped = 0
        total_failed = 0
        total_symbols = 0
        total_imports = 0

        symbol_type_counts: dict[str, int] = {
            "function": 0,
            "class": 0,
            "method": 0,
            "interface": 0,
            "variable": 0,
            "other": 0,
        }

        for file in all_files:
            lang = file.language or ""
            if (
                not lang
                or file.is_binary
                or not registry.is_supported(file.extension or lang)
            ):
                total_skipped += 1
                continue

            if file.parsed and not req.force:
                total_skipped += 1
                continue

            lang_stat = by_lang_stats.setdefault(
                lang, LanguageParseStats(language=lang)
            )

            try:
                content = await self._read_file_content(file.absolute_path)
                if content is None:
                    total_failed += 1
                    lang_stat.errors += 1
                    continue

                parse_res = self._extractor.extract(content, file.extension or lang)

                # Clear previous symbols & imports if forcing re-parse
                if file.parsed:
                    await self._symbol_repo.delete_by_file(file.id)
                    await self._import_repo.delete_by_file(file.id)

                # Persist extracted symbols with parent mapping
                symbol_db_ids: list[UUID] = []
                symbol_rows: list[dict[str, Any]] = []

                for sym in parse_res.symbols:
                    import uuid

                    sym_id = uuid.uuid4()
                    symbol_db_ids.append(sym_id)

                    parent_id = (
                        symbol_db_ids[sym.parent_index]
                        if sym.parent_index is not None
                        and sym.parent_index < len(symbol_db_ids)
                        else None
                    )

                    symbol_rows.append(
                        {
                            "id": sym_id,
                            "repository_id": repo_id,
                            "file_id": file.id,
                            "name": sym.name,
                            "symbol_type": sym.symbol_type.value
                            if hasattr(sym.symbol_type, "value")
                            else str(sym.symbol_type),
                            "language": lang,
                            "parent_symbol_id": parent_id,
                            "start_line": sym.start_line,
                            "end_line": sym.end_line,
                            "start_column": sym.start_column,
                            "end_column": sym.end_column,
                            "visibility": sym.visibility.value
                            if sym.visibility and hasattr(sym.visibility, "value")
                            else (str(sym.visibility) if sym.visibility else None),
                            "signature": sym.signature,
                            "docstring": sym.docstring,
                        }
                    )

                    # Tally symbol types
                    st_str = (
                        sym.symbol_type.value
                        if hasattr(sym.symbol_type, "value")
                        else str(sym.symbol_type)
                    )
                    if st_str in (
                        "function",
                        "class",
                        "method",
                        "interface",
                        "variable",
                    ):
                        symbol_type_counts[st_str] += 1
                    else:
                        symbol_type_counts["other"] += 1

                import_rows: list[dict[str, Any]] = [
                    {
                        "repository_id": repo_id,
                        "file_id": file.id,
                        "source_symbol": imp.source_symbol,
                        "target_module": imp.target_module,
                        "import_type": imp.import_type.value
                        if hasattr(imp.import_type, "value")
                        else str(imp.import_type),
                        "alias": imp.alias,
                    }
                    for imp in parse_res.imports
                ]

                if symbol_rows:
                    await self._symbol_repo.bulk_insert(symbol_rows)
                if import_rows:
                    await self._import_repo.bulk_insert(import_rows)

                # Update file status
                file.parsed = True
                file.symbols_count = len(symbol_rows)

                total_parsed += 1
                lang_stat.files_parsed += 1
                lang_stat.symbols_extracted += len(symbol_rows)
                lang_stat.imports_extracted += len(import_rows)

                total_symbols += len(symbol_rows)
                total_imports += len(import_rows)

            except Exception as err:
                logger.error(
                    "parse_file_failed", file=file.relative_path, error=str(err)
                )
                total_failed += 1
                lang_stat.errors += 1

        # Reset repo status to ready
        await self._repo_repo.update_status(repo_id, RepositoryStatus.ready)
        await self._db.commit()

        parse_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        stats_resp = ParseStatsResponse(
            total_files_parsed=total_parsed,
            total_files_skipped=total_skipped,
            total_files_failed=total_failed,
            total_symbols=total_symbols,
            total_imports=total_imports,
            by_language=list(by_lang_stats.values()),
            functions=symbol_type_counts["function"],
            classes=symbol_type_counts["class"],
            methods=symbol_type_counts["method"],
            interfaces=symbol_type_counts["interface"],
            variables=symbol_type_counts["variable"],
            other_symbols=symbol_type_counts["other"],
        )

        return ParseResponse(
            repository_id=repo_id,
            status=RepositoryStatus.ready.value,
            parse_time_ms=parse_time_ms,
            stats=stats_resp,
        )

    async def _read_file_content(self, abs_path: str) -> str | None:
        path = Path(abs_path)
        if not path.exists():
            return None
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: path.read_text(encoding="utf-8", errors="replace")
        )
