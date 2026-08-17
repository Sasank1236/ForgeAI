"use client";

import { useState, useEffect } from "react";
import {
  FileCode,
  Folder,
  Loader2,
  Search,
  Code2,
  FileText,
  Layers,
  Sparkles,
  GitBranch,
} from "lucide-react";
import {
  listFiles,
  listRepositories,
  listSymbols,
} from "@/lib/api";
import type { RepositoryFile, RepositoryListItem } from "@/types/repository";
import type { CodeSymbol } from "@/types/parser";

export function CodeExplorer() {
  const [repos, setRepos] = useState<RepositoryListItem[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [files, setFiles] = useState<RepositoryFile[]>([]);
  const [symbols, setSymbols] = useState<CodeSymbol[]>([]);
  const [selectedFile, setSelectedFile] = useState<RepositoryFile | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingSymbols, setLoadingSymbols] = useState(false);

  // Fetch repositories
  useEffect(() => {
    let isMounted = true;
    listRepositories()
      .then((data) => {
        if (isMounted) {
          setRepos(data);
          if (data.length > 0) {
            setSelectedRepoId(data[0].id);
          }
        }
      })
      .finally(() => {
        if (isMounted) setLoadingRepos(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch files when selected repository changes
  useEffect(() => {
    if (!selectedRepoId) return;
    let isMounted = true;
    setLoadingFiles(true);
    listFiles(selectedRepoId, 1, 100)
      .then((res) => {
        if (isMounted) {
          setFiles(res.files);
          if (res.files.length > 0) {
            setSelectedFile(res.files[0]);
          } else {
            setSelectedFile(null);
          }
        }
      })
      .catch(() => {
        if (isMounted) setFiles([]);
      })
      .finally(() => {
        if (isMounted) setLoadingFiles(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedRepoId]);

  // Fetch AST symbols when selected repository changes
  useEffect(() => {
    if (!selectedRepoId) return;
    let isMounted = true;
    setLoadingSymbols(true);
    listSymbols(selectedRepoId, { page_size: 100 })
      .then((res) => {
        if (isMounted) setSymbols(res.items);
      })
      .catch(() => {
        if (isMounted) setSymbols([]);
      })
      .finally(() => {
        if (isMounted) setLoadingSymbols(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedRepoId]);

  // Filter files by search query
  const filteredFiles = files.filter((f) =>
    f.relative_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Symbols for the currently selected file
  const fileSymbols = symbols.filter(
    (s) => selectedFile && s.file_id === selectedFile.id
  );

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-gray-950 text-gray-100">
      {/* ── File Explorer Sidebar ────────────────────────────────────────── */}
      <aside className="w-80 border-r border-gray-800 bg-gray-900/60 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Code Explorer
            </span>
            <span className="text-[11px] text-blue-400 font-mono flex items-center gap-1">
              <GitBranch size={12} />
              Repository
            </span>
          </div>

          <select
            className="w-full bg-gray-900 border border-gray-800 rounded-lg text-xs p-2 text-gray-200 focus:outline-none focus:border-blue-500"
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            disabled={loadingRepos}
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 text-gray-500" size={13} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter files by path..."
              className="w-full bg-gray-900 border border-gray-800 rounded-lg text-xs py-2 pl-8 pr-3 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* File Tree List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider px-2 py-1 block">
            Indexed Files ({filteredFiles.length})
          </span>
          {loadingFiles ? (
            <div className="py-8 flex justify-center text-gray-500">
              <Loader2 size={16} className="animate-spin" />
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-500">
              No files found in this repository.
            </div>
          ) : (
            filteredFiles.map((file) => {
              const isSelected = selectedFile?.id === file.id;
              return (
                <button
                  key={file.id}
                  onClick={() => setSelectedFile(file)}
                  className={`w-full flex items-center justify-between p-2.5 rounded-lg text-xs transition-all text-left ${
                    isSelected
                      ? "bg-blue-600/20 text-blue-400 border border-blue-800/60 font-medium"
                      : "text-gray-300 hover:bg-gray-800/60 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileCode size={14} className={isSelected ? "text-blue-400" : "text-gray-500"} />
                    <span className="truncate">{file.relative_path}</span>
                  </div>
                  {file.language && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 font-mono shrink-0">
                      {file.language}
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* ── Main Code Viewer & AST Symbol Inspector ─────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-gray-950">
        {selectedFile ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Header file bar */}
            <div className="p-4 border-b border-gray-800 bg-gray-900/40 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-blue-950 border border-blue-800 text-blue-400">
                  <FileCode size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-gray-100 font-mono">
                    {selectedFile.relative_path}
                  </h2>
                  <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5 font-mono">
                    <span>{selectedFile.language || "Plain Text"}</span>
                    <span>•</span>
                    <span>{selectedFile.line_count ?? 0} lines</span>
                    <span>•</span>
                    <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-gray-900 border border-gray-800 text-xs font-mono text-emerald-400 flex items-center gap-1.5">
                  <Layers size={13} />
                  {fileSymbols.length} AST Symbols
                </span>
              </div>
            </div>

            {/* Split view: Code content & AST Symbol list */}
            <div className="flex-1 flex overflow-hidden">
              {/* File details & preview */}
              <div className="flex-1 p-6 overflow-y-auto space-y-4">
                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-3">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    <FileText size={14} className="text-blue-400" />
                    File Metadata Specification
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 rounded-lg bg-gray-950 border border-gray-800">
                      <span className="text-gray-500 block text-[11px]">Extension</span>
                      <span className="font-mono text-gray-200 font-medium">
                        {selectedFile.extension || "N/A"}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-950 border border-gray-800">
                      <span className="text-gray-500 block text-[11px]">MIME Type</span>
                      <span className="font-mono text-gray-200 font-medium">
                        {selectedFile.mime_type || "text/plain"}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-950 border border-gray-800">
                      <span className="text-gray-500 block text-[11px]">Line Count</span>
                      <span className="font-mono text-gray-200 font-medium">
                        {selectedFile.line_count ?? 0}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-950 border border-gray-800">
                      <span className="text-gray-500 block text-[11px]">File Size</span>
                      <span className="font-mono text-gray-200 font-medium">
                        {selectedFile.size} B
                      </span>
                    </div>
                  </div>
                </div>

                {/* Path display */}
                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    <Folder size={14} className="text-blue-400" />
                    Absolute System Path
                  </span>
                  <p className="font-mono text-xs text-blue-300 break-all bg-gray-950 p-3 rounded-lg border border-gray-800">
                    {selectedFile.absolute_path}
                  </p>
                </div>
              </div>

              {/* AST Symbol panel */}
              <div className="w-80 border-l border-gray-800 bg-gray-900/40 p-4 overflow-y-auto space-y-3 shrink-0">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                  <Code2 size={14} className="text-blue-400" />
                  Tree-Sitter Symbols ({fileSymbols.length})
                </span>

                {loadingSymbols ? (
                  <div className="py-8 flex justify-center text-gray-500">
                    <Loader2 size={16} className="animate-spin" />
                  </div>
                ) : fileSymbols.length === 0 ? (
                  <div className="p-4 text-center text-xs text-gray-500 rounded-xl bg-gray-900 border border-gray-800">
                    No AST symbols parsed for this file.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {fileSymbols.map((s) => (
                      <div
                        key={s.id}
                        className="p-3 rounded-xl bg-gray-900 border border-gray-800 space-y-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-gray-100 truncate">
                            {s.name}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 font-mono border border-blue-900">
                            {s.symbol_type}
                          </span>
                        </div>
                        {s.signature && (
                          <p className="font-mono text-[11px] text-gray-400 truncate">
                            {s.signature}
                          </p>
                        )}
                        <div className="flex items-center justify-between text-[11px] text-gray-500 pt-1 border-t border-gray-800/60 font-mono">
                          <span>
                            L{s.start_line}-{s.end_line}
                          </span>
                          {s.visibility && (
                            <span className="text-emerald-400 capitalize">{s.visibility}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 max-w-lg mx-auto">
            <div className="w-12 h-12 rounded-2xl bg-blue-950 border border-blue-800 flex items-center justify-center text-blue-400">
              <Sparkles size={24} />
            </div>
            <h3 className="font-bold text-lg text-gray-100">Code Explorer & AST Inspector</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Select an indexed file from the left sidebar to inspect its Tree-sitter AST symbols, location markers, and metadata specifications.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
