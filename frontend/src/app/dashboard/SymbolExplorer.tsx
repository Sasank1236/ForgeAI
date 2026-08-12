"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Code,
  FileText,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Cpu,
  Layers,
  Sparkles,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import { listSymbols, listImports, parseRepository } from "@/lib/api";
import type {
  SymbolResponse,
  ImportRecordResponse,
  ParseResponse,
} from "@/types/parser";
import type { RepositoryListItem } from "@/types/repository";

interface SymbolExplorerProps {
  repo: RepositoryListItem;
  onClose?: () => void;
}

export function SymbolExplorer({ repo, onClose }: SymbolExplorerProps) {
  const [activeTab, setActiveTab] = useState<"symbols" | "imports" | "parse">("symbols");

  // Parse State
  const [parsing, setParsing] = useState(false);
  const [parseResult, setParseResult] = useState<ParseResponse | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  // Symbols State
  const [symbols, setSymbols] = useState<SymbolResponse[]>([]);
  const [symbolsTotal, setSymbolsTotal] = useState(0);
  const [symbolsPage, setSymbolsPage] = useState(1);
  const [symbolType, setSymbolType] = useState<string>("");
  const [symbolNameQuery, setSymbolNameQuery] = useState<string>("");
  const [loadingSymbols, setLoadingSymbols] = useState(false);

  // Imports State
  const [imports, setImports] = useState<ImportRecordResponse[]>([]);
  const [importsTotal, setImportsTotal] = useState(0);
  const [importsPage, setImportsPage] = useState(1);
  const [importType, setImportType] = useState<string>("");
  const [importModuleQuery, setImportModuleQuery] = useState<string>("");
  const [loadingImports, setLoadingImports] = useState(false);

  // Selected symbol for detail modal / drawer
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolResponse | null>(null);

  // ── Fetch Symbols ────────────────────────────────────────────────────────────
  const fetchSymbolsData = useCallback(async () => {
    setLoadingSymbols(true);
    try {
      const res = await listSymbols(repo.id, {
        page: symbolsPage,
        page_size: 25,
        symbol_type: symbolType || undefined,
        name_query: symbolNameQuery || undefined,
      });
      setSymbols(res.items);
      setSymbolsTotal(res.total);
    } catch {
      setSymbols([]);
      setSymbolsTotal(0);
    } finally {
      setLoadingSymbols(false);
    }
  }, [repo.id, symbolsPage, symbolType, symbolNameQuery]);

  // ── Fetch Imports ────────────────────────────────────────────────────────────
  const fetchImportsData = useCallback(async () => {
    setLoadingImports(true);
    try {
      const res = await listImports(repo.id, {
        page: importsPage,
        page_size: 25,
        import_type: importType || undefined,
        module_query: importModuleQuery || undefined,
      });
      setImports(res.items);
      setImportsTotal(res.total);
    } catch {
      setImports([]);
      setImportsTotal(0);
    } finally {
      setLoadingImports(false);
    }
  }, [repo.id, importsPage, importType, importModuleQuery]);

  useEffect(() => {
    let isMounted = true;
    if (activeTab === "symbols") {
      listSymbols(repo.id, {
        page: symbolsPage,
        page_size: 25,
        symbol_type: symbolType || undefined,
        name_query: symbolNameQuery || undefined,
      })
        .then((res) => {
          if (isMounted) {
            setSymbols(res.items);
            setSymbolsTotal(res.total);
          }
        })
        .catch(() => {
          if (isMounted) {
            setSymbols([]);
            setSymbolsTotal(0);
          }
        })
        .finally(() => {
          if (isMounted) setLoadingSymbols(false);
        });
    } else if (activeTab === "imports") {
      listImports(repo.id, {
        page: importsPage,
        page_size: 25,
        import_type: importType || undefined,
        module_query: importModuleQuery || undefined,
      })
        .then((res) => {
          if (isMounted) {
            setImports(res.items);
            setImportsTotal(res.total);
          }
        })
        .catch(() => {
          if (isMounted) {
            setImports([]);
            setImportsTotal(0);
          }
        })
        .finally(() => {
          if (isMounted) setLoadingImports(false);
        });
    }
    return () => {
      isMounted = false;
    };
  }, [
    activeTab,
    repo.id,
    symbolsPage,
    symbolType,
    symbolNameQuery,
    importsPage,
    importType,
    importModuleQuery,
  ]);

  // ── Handle Trigger Parse ──────────────────────────────────────────────────────
  const handleRunParse = async (force = false) => {
    setParsing(true);
    setParseError(null);
    try {
      const res = await parseRepository(repo.id, { force_reparse: force });
      setParseResult(res);
      fetchSymbolsData();
      fetchImportsData();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Parsing failed. Check backend logs.";
      setParseError(msg);
    } finally {
      setParsing(false);
    }
  };

  const symbolTypesList = [
    "function",
    "class",
    "method",
    "constructor",
    "interface",
    "enum",
    "struct",
    "variable",
    "constant",
    "type_alias",
    "module",
    "namespace",
  ];

  const importTypesList = [
    "import",
    "from_import",
    "require",
    "dynamic_import",
    "include",
    "package",
    "export",
    "re_export",
    "side_effect",
  ];

  return (
    <div
      className="card animate-fade-in mt-6"
      style={{
        background: "var(--color-surface-overlay)",
        border: "1px solid var(--color-brand-800)",
      }}
    >
      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "var(--gradient-brand)" }}
          >
            <Cpu size={20} className="text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-base text-gray-100">{repo.name}</h2>
              <span className="text-xs px-2 py-0.5 rounded-md bg-blue-950 text-blue-400 border border-blue-800 font-mono">
                Code Intelligence
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Tree-sitter AST Symbol & Dependency Extraction
            </p>
          </div>
        </div>

        {/* Tab Controls & Parse CTA */}
        <div className="flex items-center gap-3">
          <div className="flex bg-gray-900/80 p-1 rounded-xl border border-gray-800 text-xs">
            <button
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeTab === "symbols"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              onClick={() => setActiveTab("symbols")}
            >
              <Code size={13} className="inline mr-1.5" />
              Symbols ({symbolsTotal})
            </button>
            <button
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeTab === "imports"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              onClick={() => setActiveTab("imports")}
            >
              <Layers size={13} className="inline mr-1.5" />
              Imports ({importsTotal})
            </button>
            <button
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeTab === "parse"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              onClick={() => setActiveTab("parse")}
            >
              <Sparkles size={13} className="inline mr-1.5" />
              Parse Config
            </button>
          </div>

          <button
            className="btn btn-primary text-xs px-3 py-1.5"
            onClick={() => handleRunParse(false)}
            disabled={parsing}
          >
            {parsing ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                Parsing AST…
              </>
            ) : (
              <>
                <Cpu size={13} />
                Parse Repo
              </>
            )}
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-200 text-xs px-2 py-1"
            >
              Close
            </button>
          )}
        </div>
      </div>

      {/* ── TAB 1: SYMBOLS EXPLORER ──────────────────────────────────────────── */}
      {activeTab === "symbols" && (
        <div className="pt-4 space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap gap-3 items-center justify-between bg-gray-900/60 p-3 rounded-xl border border-gray-800">
            <div className="flex items-center gap-2 flex-1 min-w-[240px]">
              <Search size={14} className="text-gray-400 shrink-0" />
              <input
                type="text"
                placeholder="Search symbol name (e.g. parse_repository, SymbolRepo)..."
                className="input text-xs py-1.5 w-full font-mono"
                value={symbolNameQuery}
                onChange={(e) => {
                  setSymbolNameQuery(e.target.value);
                  setSymbolsPage(1);
                }}
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter size={14} className="text-gray-400" />
              <select
                className="input text-xs py-1.5 font-mono"
                value={symbolType}
                onChange={(e) => {
                  setSymbolType(e.target.value);
                  setSymbolsPage(1);
                }}
              >
                <option value="">All Symbol Types</option>
                {symbolTypesList.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Symbols List */}
          {loadingSymbols ? (
            <div className="py-12 flex justify-center items-center text-gray-400 gap-2 text-sm">
              <Loader2 size={16} className="animate-spin text-blue-500" />
              Loading extracted symbols...
            </div>
          ) : symbols.length === 0 ? (
            <div className="py-12 text-center text-gray-400 bg-gray-950/40 rounded-xl border border-gray-800">
              <Code size={28} className="mx-auto mb-2 text-gray-600" />
              <p className="font-semibold text-sm text-gray-300">No symbols found</p>
              <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                If you haven&apos;t parsed this repository yet, click &quot;Parse Repo&quot; above to extract AST symbols.
              </p>
              <button
                className="btn btn-secondary text-xs mt-4"
                onClick={() => handleRunParse(false)}
                disabled={parsing}
              >
                Run Parser Now
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {symbols.map((sym) => (
                <div
                  key={sym.id}
                  onClick={() => setSelectedSymbol(sym)}
                  className="group flex items-start justify-between p-3 rounded-xl bg-gray-900/40 hover:bg-gray-800/60 border border-gray-800/80 transition-all cursor-pointer"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-blue-400 group-hover:text-blue-300">
                        {sym.name}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-950/80 text-blue-400 border border-blue-800/60 font-mono">
                        {sym.symbol_type}
                      </span>
                      {sym.visibility && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 font-mono">
                          {sym.visibility}
                        </span>
                      )}
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800/50 font-mono">
                        {sym.language}
                      </span>
                    </div>

                    {sym.signature && (
                      <p className="text-xs font-mono text-gray-300 bg-gray-950/60 px-2 py-1 rounded border border-gray-800/60 max-w-2xl truncate">
                        {sym.signature}
                      </p>
                    )}

                    {sym.docstring && (
                      <p className="text-xs text-gray-400 italic line-clamp-1">
                        &quot;{sym.docstring.trim()}&quot;
                      </p>
                    )}
                  </div>

                  <div className="text-right shrink-0">
                    <span className="text-xs font-mono text-gray-400 flex items-center gap-1 justify-end">
                      <FileText size={12} className="text-gray-500" />
                      L{sym.start_line}-L{sym.end_line}
                    </span>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              <div className="flex items-center justify-between pt-2 text-xs text-gray-400">
                <span>
                  Showing page {symbolsPage} of {Math.ceil(symbolsTotal / 25) || 1} ({symbolsTotal} total symbols)
                </span>
                <div className="flex gap-2">
                  <button
                    className="btn btn-secondary text-xs px-2.5 py-1"
                    disabled={symbolsPage <= 1}
                    onClick={() => setSymbolsPage((p) => p - 1)}
                  >
                    <ChevronLeft size={13} /> Prev
                  </button>
                  <button
                    className="btn btn-secondary text-xs px-2.5 py-1"
                    disabled={symbolsPage * 25 >= symbolsTotal}
                    onClick={() => setSymbolsPage((p) => p + 1)}
                  >
                    Next <ChevronRight size={13} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: IMPORTS EXPLORER ──────────────────────────────────────────── */}
      {activeTab === "imports" && (
        <div className="pt-4 space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap gap-3 items-center justify-between bg-gray-900/60 p-3 rounded-xl border border-gray-800">
            <div className="flex items-center gap-2 flex-1 min-w-[240px]">
              <Search size={14} className="text-gray-400 shrink-0" />
              <input
                type="text"
                placeholder="Search target module (e.g. sqlalchemy, react, os)..."
                className="input text-xs py-1.5 w-full font-mono"
                value={importModuleQuery}
                onChange={(e) => {
                  setImportModuleQuery(e.target.value);
                  setImportsPage(1);
                }}
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter size={14} className="text-gray-400" />
              <select
                className="input text-xs py-1.5 font-mono"
                value={importType}
                onChange={(e) => {
                  setImportType(e.target.value);
                  setImportsPage(1);
                }}
              >
                <option value="">All Import Types</option>
                {importTypesList.map((it) => (
                  <option key={it} value={it}>
                    {it}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Imports List */}
          {loadingImports ? (
            <div className="py-12 flex justify-center items-center text-gray-400 gap-2 text-sm">
              <Loader2 size={16} className="animate-spin text-blue-500" />
              Loading import dependencies...
            </div>
          ) : imports.length === 0 ? (
            <div className="py-12 text-center text-gray-400 bg-gray-950/40 rounded-xl border border-gray-800">
              <Layers size={28} className="mx-auto mb-2 text-gray-600" />
              <p className="font-semibold text-sm text-gray-300">No imports found</p>
              <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                Run repository parsing to extract dependency graph imports.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {imports.map((imp) => (
                <div
                  key={imp.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-gray-900/40 border border-gray-800/80 font-mono text-xs"
                >
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60 text-[10px]">
                      {imp.import_type}
                    </span>
                    <span className="font-semibold text-gray-200">
                      {imp.target_module}
                    </span>
                    {imp.source_symbol && (
                      <span className="text-gray-400">
                        → <span className="text-blue-400">{imp.source_symbol}</span>
                      </span>
                    )}
                    {imp.alias && (
                      <span className="text-purple-400">as {imp.alias}</span>
                    )}
                  </div>
                </div>
              ))}

              {/* Pagination */}
              <div className="flex items-center justify-between pt-2 text-xs text-gray-400">
                <span>
                  Showing page {importsPage} of {Math.ceil(importsTotal / 25) || 1} ({importsTotal} total imports)
                </span>
                <div className="flex gap-2">
                  <button
                    className="btn btn-secondary text-xs px-2.5 py-1"
                    disabled={importsPage <= 1}
                    onClick={() => setImportsPage((p) => p - 1)}
                  >
                    <ChevronLeft size={13} /> Prev
                  </button>
                  <button
                    className="btn btn-secondary text-xs px-2.5 py-1"
                    disabled={importsPage * 25 >= importsTotal}
                    onClick={() => setImportsPage((p) => p + 1)}
                  >
                    Next <ChevronRight size={13} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 3: PARSE CONFIG & STATS ──────────────────────────────────────── */}
      {activeTab === "parse" && (
        <div className="pt-4 space-y-4">
          <div className="bg-gray-900/60 p-4 rounded-xl border border-gray-800 space-y-3">
            <h3 className="font-bold text-sm text-gray-200 flex items-center gap-2">
              <Cpu size={15} className="text-blue-400" />
              AST Parser Settings
            </h3>
            <p className="text-xs text-gray-400">
              ForgeAI uses official Tree-sitter C/Python bindings to perform high-speed AST traversal for Python, JavaScript, TypeScript, TSX, Java, C++, Go, and Rust.
            </p>

            <div className="flex items-center gap-3 pt-2">
              <button
                className="btn btn-primary text-xs px-4 py-2"
                onClick={() => handleRunParse(false)}
                disabled={parsing}
              >
                {parsing ? "Parsing..." : "Parse New/Modified Files"}
              </button>
              <button
                className="btn btn-secondary text-xs px-4 py-2"
                onClick={() => handleRunParse(true)}
                disabled={parsing}
              >
                Force Full Re-Parse
              </button>
            </div>
          </div>

          {/* Parse Result Summary */}
          {parseError && (
            <div className="p-3 rounded-xl bg-red-950/40 border border-red-800 text-red-400 text-xs flex items-center gap-2">
              <AlertTriangle size={15} />
              {parseError}
            </div>
          )}

          {parseResult && (
            <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-3">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                <CheckCircle size={16} />
                Parsing Completed in {parseResult.stats.duration_ms}ms
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 rounded-lg bg-gray-950 border border-gray-800">
                  <span className="text-gray-400 block">Files Parsed</span>
                  <strong className="text-base text-gray-100">
                    {parseResult.stats.total_files_parsed}
                  </strong>
                </div>
                <div className="p-2.5 rounded-lg bg-gray-950 border border-gray-800">
                  <span className="text-gray-400 block">Symbols Extracted</span>
                  <strong className="text-base text-blue-400">
                    {parseResult.stats.total_symbols_extracted}
                  </strong>
                </div>
                <div className="p-2.5 rounded-lg bg-gray-950 border border-gray-800">
                  <span className="text-gray-400 block">Imports Extracted</span>
                  <strong className="text-base text-emerald-400">
                    {parseResult.stats.total_imports_extracted}
                  </strong>
                </div>
                <div className="p-2.5 rounded-lg bg-gray-950 border border-gray-800">
                  <span className="text-gray-400 block">Parse Failures</span>
                  <strong className="text-base text-red-400">
                    {parseResult.stats.total_failed_files}
                  </strong>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Symbol Detail Modal ──────────────────────────────────────────────── */}
      {selectedSymbol && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <Code size={18} className="text-blue-400" />
                <h3 className="font-bold text-base text-gray-100">
                  {selectedSymbol.name}
                </h3>
              </div>
              <button
                className="text-gray-400 hover:text-gray-200 text-xs px-2 py-1"
                onClick={() => setSelectedSymbol(null)}
              >
                Close
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-gray-400 block mb-1">Symbol Type & Language</span>
                <span className="font-mono px-2 py-1 rounded bg-blue-950 text-blue-300 mr-2">
                  {selectedSymbol.symbol_type}
                </span>
                <span className="font-mono px-2 py-1 rounded bg-purple-950 text-purple-300">
                  {selectedSymbol.language}
                </span>
              </div>

              <div>
                <span className="text-gray-400 block mb-1">Position</span>
                <span className="font-mono text-gray-200">
                  Lines {selectedSymbol.start_line} – {selectedSymbol.end_line}
                </span>
              </div>

              {selectedSymbol.signature && (
                <div>
                  <span className="text-gray-400 block mb-1">Signature</span>
                  <pre className="p-3 rounded-lg bg-gray-950 font-mono text-gray-200 border border-gray-800 overflow-x-auto">
                    {selectedSymbol.signature}
                  </pre>
                </div>
              )}

              {selectedSymbol.docstring && (
                <div>
                  <span className="text-gray-400 block mb-1">Docstring</span>
                  <div className="p-3 rounded-lg bg-gray-950 text-gray-300 border border-gray-800 whitespace-pre-wrap">
                    {selectedSymbol.docstring}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
