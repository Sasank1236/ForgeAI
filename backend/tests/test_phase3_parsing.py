"""Comprehensive test suite for Phase 3: Tree-sitter Code Parsing & Code Intelligence.

Covers all 5 tasks in Phase 3:
  - Task 1: Symbol and Import ORM database models & Alembic migration schema
  - Task 2: Symbol, Import, and Parser Pydantic schemas
  - Task 3: SymbolRepo and ImportRepo data access layer
  - Task 4: TreeSitterRegistry language grammar registry
  - Task 5: CodeParserService, ASTExtractor across languages & REST API endpoints
"""

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.file import RepositoryFile
from forgeai.models.import_ import Import, ImportType
from forgeai.models.repository import Repository, RepositoryStatus
from forgeai.models.symbol import Symbol, SymbolType, Visibility
from forgeai.repositories.import_repo import ImportRepo
from forgeai.repositories.symbol_repo import SymbolRepo
from forgeai.schemas.import_ import (
    ImportFilter,
    ImportListResponse,
    ImportRecordResponse,
)
from forgeai.schemas.parser import (
    LanguageParseStats,
    ParseRequest,
    ParseResponse,
    ParseStatsResponse,
)
from forgeai.schemas.symbol import (
    SymbolFilter,
    SymbolListResponse,
    SymbolResponse,
)
from forgeai.services.parser import ASTExtractor, CodeParserService
from forgeai.services.tree_sitter_registry import TreeSitterRegistry

# ── Task 1 Tests: Symbol & Import Database Models ─────────────────────────────


def test_symbol_model_fields_and_enums() -> None:
    """Task 1: Verify Symbol ORM model initialization and Enum values."""
    sym_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()

    sym = Symbol(
        id=sym_id,
        repository_id=repo_id,
        file_id=file_id,
        name="test_func",
        symbol_type=SymbolType.function,
        language="Python",
        start_line=10,
        end_line=20,
        start_column=0,
        end_column=15,
        visibility=Visibility.public,
        signature="def test_func(x: int) -> str",
        docstring="Sample docstring",
    )

    assert sym.id == sym_id
    assert sym.repository_id == repo_id
    assert sym.file_id == file_id
    assert sym.name == "test_func"
    assert sym.symbol_type == SymbolType.function
    assert sym.visibility == Visibility.public
    assert "test_func" in repr(sym)


def test_import_model_fields_and_enums() -> None:
    """Task 1: Verify Import ORM model initialization and Enum values."""
    imp_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()

    imp = Import(
        id=imp_id,
        repository_id=repo_id,
        file_id=file_id,
        source_symbol="useState",
        target_module="react",
        import_type=ImportType.from_import,
        alias="useReactState",
    )

    assert imp.id == imp_id
    assert imp.target_module == "react"
    assert imp.source_symbol == "useState"
    assert imp.import_type == ImportType.from_import
    assert imp.alias == "useReactState"
    assert "react" in repr(imp)


# ── Task 2 Tests: Pydantic Schemas ───────────────────────────────────────────


def test_symbol_pydantic_schemas() -> None:
    """Task 2: Verify Symbol Pydantic DTOs validation and serialization."""
    sym_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()

    resp = SymbolResponse(
        id=sym_id,
        repository_id=repo_id,
        file_id=file_id,
        name="MyClass",
        symbol_type=SymbolType.class_,
        language="TypeScript",
        start_line=1,
        end_line=50,
        start_column=0,
        end_column=1,
        visibility=Visibility.public,
        signature="class MyClass",
    )
    assert resp.name == "MyClass"
    assert resp.symbol_type == SymbolType.class_

    list_resp = SymbolListResponse(items=[resp], total=1, page=1, page_size=50)
    assert list_resp.total == 1
    assert list_resp.items[0].name == "MyClass"

    filt = SymbolFilter(name_contains="MyClass", symbol_type=SymbolType.class_)
    assert filt.name_contains == "MyClass"


def test_import_pydantic_schemas() -> None:
    """Task 2: Verify Import Pydantic DTOs validation and serialization."""
    imp_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()

    resp = ImportRecordResponse(
        id=imp_id,
        repository_id=repo_id,
        file_id=file_id,
        source_symbol="path",
        target_module="os",
        import_type=ImportType.from_import,
        alias="p",
    )
    assert resp.target_module == "os"
    assert resp.import_type == ImportType.from_import

    list_resp = ImportListResponse(items=[resp], total=1, page=1, page_size=50)
    assert list_resp.total == 1

    filt = ImportFilter(target_module_contains="os")
    assert filt.target_module_contains == "os"


def test_parser_pydantic_schemas() -> None:
    """Task 2: Verify Parser Pydantic DTOs validation and serialization."""
    req = ParseRequest(force=True, languages=["Python"])
    assert req.force is True
    assert req.languages == ["Python"]

    lang_stats = LanguageParseStats(
        language="Python", files_parsed=5, symbols_extracted=20, imports_extracted=10
    )
    stats_resp = ParseStatsResponse(
        total_files_parsed=5,
        total_symbols=20,
        total_imports=10,
        by_language=[lang_stats],
        functions=15,
        classes=5,
    )
    repo_id = uuid.uuid4()
    parse_resp = ParseResponse(
        repository_id=repo_id,
        status="ready",
        parse_time_ms=120,
        stats=stats_resp,
    )
    assert parse_resp.status == "ready"
    assert parse_resp.stats.total_symbols == 20


# ── Task 3 Tests: Repositories ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_symbol_repo_crud_and_stats(db_session: AsyncSession) -> None:
    """Task 3: Test SymbolRepo bulk insert, get_by_id, list_by_repo, and stats."""
    repo = Repository(
        name="test_repo", root_path="/tmp/test_repo", status=RepositoryStatus.ready
    )
    db_session.add(repo)
    await db_session.flush()

    file_rec = RepositoryFile(
        repository_id=repo.id,
        relative_path="main.py",
        absolute_path="/tmp/test_repo/main.py",
        language="Python",
        extension=".py",
    )
    db_session.add(file_rec)
    await db_session.commit()

    symbol_repo = SymbolRepo(db_session)

    s1_id = uuid.uuid4()
    s2_id = uuid.uuid4()

    rows = [
        {
            "id": s1_id,
            "repository_id": repo.id,
            "file_id": file_rec.id,
            "name": "foo",
            "symbol_type": SymbolType.function,
            "language": "Python",
            "start_line": 1,
            "end_line": 5,
            "start_column": 0,
            "end_column": 10,
            "visibility": Visibility.public,
        },
        {
            "id": s2_id,
            "repository_id": repo.id,
            "file_id": file_rec.id,
            "name": "BarClass",
            "symbol_type": SymbolType.class_,
            "language": "Python",
            "start_line": 10,
            "end_line": 20,
            "start_column": 0,
            "end_column": 10,
            "visibility": Visibility.public,
        },
    ]

    inserted = await symbol_repo.bulk_insert(rows)
    await db_session.commit()
    assert inserted == 2

    s1 = await symbol_repo.get_by_id(s1_id)
    assert s1 is not None
    assert s1.name == "foo"

    symbols, total = await symbol_repo.list_by_repo(repo.id, name_query="foo")
    assert total == 1
    assert symbols[0].name == "foo"

    by_file = await symbol_repo.list_by_file(file_rec.id)
    assert len(by_file) == 2

    stats = await symbol_repo.get_stats_by_repo(repo.id)
    assert stats.get("function") == 1
    assert stats.get("class") == 1

    count = await symbol_repo.count_by_repo(repo.id)
    assert count == 2

    deleted = await symbol_repo.delete_by_file(file_rec.id)
    await db_session.commit()
    assert deleted == 2


@pytest.mark.asyncio
async def test_import_repo_crud(db_session: AsyncSession) -> None:
    """Task 3: Test ImportRepo bulk insert, get_by_id, list_by_repo, and count."""
    repo = Repository(
        name="test_repo_imp",
        root_path="/tmp/test_repo_imp",
        status=RepositoryStatus.ready,
    )
    db_session.add(repo)
    await db_session.flush()

    file_rec = RepositoryFile(
        repository_id=repo.id,
        relative_path="app.py",
        absolute_path="/tmp/test_repo_imp/app.py",
        language="Python",
        extension=".py",
    )
    db_session.add(file_rec)
    await db_session.commit()

    import_repo = ImportRepo(db_session)
    imp1_id = uuid.uuid4()

    rows = [
        {
            "id": imp1_id,
            "repository_id": repo.id,
            "file_id": file_rec.id,
            "source_symbol": "path",
            "target_module": "os",
            "import_type": ImportType.from_import,
            "alias": "p",
        }
    ]

    inserted = await import_repo.bulk_insert(rows)
    await db_session.commit()
    assert inserted == 1

    fetched = await import_repo.get_by_id(imp1_id)
    assert fetched is not None
    assert fetched.target_module == "os"

    imports, total = await import_repo.list_by_repo(repo.id, module_query="os")
    assert total == 1
    assert imports[0].target_module == "os"

    count = await import_repo.count_by_repo(repo.id)
    assert count == 1


# ── Task 4 Tests: TreeSitterRegistry ─────────────────────────────────────────


def test_tree_sitter_registry_languages_and_parsers() -> None:
    """Task 4: Test TreeSitterRegistry grammar registration and parser loading."""
    reg = TreeSitterRegistry()

    # Check built-in supported languages
    for ext, lang_name in [
        (".py", "Python"),
        (".js", "JavaScript"),
        (".ts", "TypeScript"),
        (".tsx", "TSX"),
        (".go", "Go"),
        (".java", "Java"),
        (".cpp", "C++"),
        (".rs", "Rust"),
    ]:
        assert reg.is_supported(ext)
        assert reg.get_canonical_name(ext) == lang_name
        parser = reg.get_parser(ext)
        assert parser is not None

    # Parse Python snippet
    py_tree = reg.parse_code("def hello(): pass", ".py")
    assert py_tree is not None
    assert py_tree.root_node.type == "module"

    # Unsupported extension
    assert not reg.is_supported(".unsupported_ext_xyz")
    assert reg.get_parser(".unsupported_ext_xyz") is None


# ── Task 5 Tests: ASTExtractor, CodeParserService & API Endpoints ────────────


def test_ast_extractor_python() -> None:
    """Task 5: Test ASTExtractor Python symbol & import extraction."""
    extractor = ASTExtractor()
    code = '''"""Module docstring."""
import os
from math import sqrt as square_root

def calculate_area(r: float) -> float:
    """Calculate area of circle."""
    return 3.14 * square_root(r)

class Circle:
    """Circle class."""
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return calculate_area(self.radius)
'''
    res = extractor.extract(code, ".py")

    assert len(res.imports) == 2
    assert res.imports[0].target_module == "os"
    assert res.imports[1].target_module == "math"
    assert res.imports[1].source_symbol == "sqrt"
    assert res.imports[1].alias == "square_root"

    symbol_names = [s.name for s in res.symbols]
    assert "calculate_area" in symbol_names
    assert "Circle" in symbol_names
    assert "__init__" in symbol_names
    assert "area" in symbol_names

    # Check docstring extraction
    circle_sym = next(s for s in res.symbols if s.name == "Circle")
    assert circle_sym.docstring == "Circle class."


def test_ast_extractor_javascript_typescript() -> None:
    """Task 5: Test ASTExtractor JS/TS symbol & import extraction."""
    extractor = ASTExtractor()
    ts_code = """import { useState, useEffect } from 'react';
import axios from 'axios';

export interface User {
  id: number;
  name: string;
}

export class UserService {
  async getUser(id: number): Promise<User> {
    return { id, name: 'Alice' };
  }
}
"""
    res = extractor.extract(ts_code, ".ts")

    assert len(res.imports) >= 2
    modules = [imp.target_module for imp in res.imports]
    assert "react" in modules
    assert "axios" in modules

    symbol_names = [s.name for s in res.symbols]
    assert "User" in symbol_names
    assert "UserService" in symbol_names
    assert "getUser" in symbol_names


def test_ast_extractor_go() -> None:
    """Task 5: Test ASTExtractor Go symbol & import extraction."""
    extractor = ASTExtractor()
    go_code = """package main

import (
    "fmt"
    "net/http"
)

type Server struct {
    Port int
}

func NewServer(port int) *Server {
    return &Server{Port: port}
}

func (s *Server) Start() error {
    fmt.Println("Starting")
    return nil
}
"""
    res = extractor.extract(go_code, ".go")

    modules = [imp.target_module for imp in res.imports]
    assert "fmt" in modules
    assert "net/http" in modules

    names = [s.name for s in res.symbols]
    assert "Server" in names
    assert "NewServer" in names
    assert "Start" in names


def test_ast_extractor_java() -> None:
    """Task 5: Test ASTExtractor Java symbol & import extraction."""
    extractor = ASTExtractor()
    java_code = """package com.example.app;

import java.util.List;
import java.util.ArrayList;

public class AppConfig {
    private String env;

    public AppConfig(String env) {
        this.env = env;
    }

    public String getEnv() {
        return this.env;
    }
}
"""
    res = extractor.extract(java_code, ".java")

    assert any(imp.import_type == ImportType.package for imp in res.imports)
    assert any("java.util" in imp.target_module for imp in res.imports)

    names = [s.name for s in res.symbols]
    assert "AppConfig" in names
    assert "getEnv" in names


def test_ast_extractor_cpp() -> None:
    """Task 5: Test ASTExtractor C++ symbol & include extraction."""
    extractor = ASTExtractor()
    cpp_code = """#include <iostream>
#include <vector>

namespace engine {
    class Physics {
    public:
        void update(float dt);
    };

    void calculate_forces() {}
}
"""
    res = extractor.extract(cpp_code, ".cpp")

    includes = [imp.target_module for imp in res.imports]
    assert "iostream" in includes
    assert "vector" in includes

    names = [s.name for s in res.symbols]
    assert "engine" in names
    assert "Physics" in names
    assert "calculate_forces" in names


def test_ast_extractor_rust() -> None:
    """Task 5: Test ASTExtractor Rust symbol & use extraction."""
    extractor = ASTExtractor()
    rust_code = """use std::collections::HashMap;

pub struct Config {
    pub key: String,
}

impl Config {
    pub fn new(key: String) -> Self {
        Self { key }
    }
}

pub fn run() {}
"""
    res = extractor.extract(rust_code, ".rs")

    assert len(res.imports) >= 1
    assert "std::collections::HashMap" in res.imports[0].target_module

    names = [s.name for s in res.symbols]
    assert "Config" in names
    assert "new" in names
    assert "run" in names


@pytest.mark.asyncio
async def test_code_parser_service_full_pipeline(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    """Task 5: Test CodeParserService parsing files on disk and saving to DB."""
    # Create temp repository files on disk
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()

    py_file = repo_dir / "math_utils.py"
    py_file.write_text(
        "import math\n\ndef add(a: int, b: int) -> int:\n    return a + b\n"
    )

    js_file = repo_dir / "index.js"
    js_file.write_text("const fs = require('fs');\nfunction main() {}\n")

    repo = Repository(
        name="sample_repo", root_path=str(repo_dir), status=RepositoryStatus.ready
    )
    db_session.add(repo)
    await db_session.flush()

    f1 = RepositoryFile(
        repository_id=repo.id,
        relative_path="math_utils.py",
        absolute_path=str(py_file),
        language="Python",
        extension=".py",
    )
    f2 = RepositoryFile(
        repository_id=repo.id,
        relative_path="index.js",
        absolute_path=str(js_file),
        language="JavaScript",
        extension=".js",
    )
    db_session.add_all([f1, f2])
    await db_session.commit()

    parser_svc = CodeParserService(db_session)
    parse_resp = await parser_svc.parse_repository(repo.id, ParseRequest(force=True))

    assert parse_resp.status == "ready"
    assert parse_resp.stats.total_files_parsed == 2
    assert parse_resp.stats.total_symbols >= 2
    assert parse_resp.stats.total_imports >= 1

    # Verify DB persistence
    sym_repo = SymbolRepo(db_session)
    symbols, total_syms = await sym_repo.list_by_repo(repo.id)
    assert total_syms >= 2

    imp_repo = ImportRepo(db_session)
    imports, total_imps = await imp_repo.list_by_repo(repo.id)
    assert total_imps >= 1


@pytest.mark.asyncio
async def test_parse_api_endpoints(
    client: AsyncClient, db_session: AsyncSession, tmp_path: Path
) -> None:
    """Task 5: Test REST API endpoints: POST /parse, GET /symbols, GET /imports."""
    repo_dir = tmp_path / "api_repo"
    repo_dir.mkdir()

    py_file = repo_dir / "service.py"
    py_file.write_text("import os\n\ndef run_service():\n    pass\n")

    repo = Repository(
        name="api_repo", root_path=str(repo_dir), status=RepositoryStatus.ready
    )
    db_session.add(repo)
    await db_session.flush()

    f1 = RepositoryFile(
        repository_id=repo.id,
        relative_path="service.py",
        absolute_path=str(py_file),
        language="Python",
        extension=".py",
    )
    db_session.add(f1)
    await db_session.commit()

    # 1. POST /api/v1/repositories/{id}/parse
    parse_res = await client.post(
        f"/api/v1/repositories/{repo.id}/parse",
        json={"force": True},
    )
    assert parse_res.status_code == 200
    data = parse_res.json()
    assert data["status"] == "ready"
    assert data["stats"]["total_files_parsed"] == 1

    # 2. GET /api/v1/repositories/{id}/symbols
    sym_res = await client.get(f"/api/v1/repositories/{repo.id}/symbols")
    assert sym_res.status_code == 200
    sym_data = sym_res.json()
    assert sym_data["total"] >= 1
    assert sym_data["items"][0]["name"] == "run_service"

    # 3. GET /api/v1/repositories/{id}/imports
    imp_res = await client.get(f"/api/v1/repositories/{repo.id}/imports")
    assert imp_res.status_code == 200
    imp_data = imp_res.json()
    assert imp_data["total"] >= 1
    assert imp_data["items"][0]["target_module"] == "os"
