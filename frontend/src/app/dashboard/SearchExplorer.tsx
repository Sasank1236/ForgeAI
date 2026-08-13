"use client";

import { useState, useCallback } from "react";
import {
  Search,
  Loader2,
  Sparkles,
  FileCode2,
  Filter,
  Layers,
  Code2,
  X,
  Hash,
  Compass,
} from "lucide-react";
import { searchRepository } from "@/lib/api";
import type {
  SearchQueryRequest,
  SearchResponse,
  SearchResultItem,
  SearchType,
} from "@/types/search";
import type { RepositoryListItem } from "@/types/repository";

interface SearchExplorerProps {
  repo: RepositoryListItem;
  onClose?: () => void;
}

export function SearchExplorer({ repo, onClose }: SearchExplorerProps) {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState<SearchType>("hybrid");
  const [language, setLanguage] = useState("");
  const [extension, setExtension] = useState("");
  const [searching, setSearching] = useState(false);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(
    async (overrideType?: SearchType) => {
      if (!query.trim()) return;
      setSearching(true);
      setError(null);
      const targetType = overrideType || searchType;
      const req: SearchQueryRequest = {
        query: query.trim(),
        search_type: targetType,
        limit: 20,
        language: language.trim() || undefined,
        extension: extension.trim() || undefined,
      };

      try {
        const res = await searchRepository(repo.id, req);
        setResponse(res);
      } catch {
        setError("Search query failed. Please verify server connection.");
      } finally {
        setSearching(false);
      }
    },
    [query, searchType, language, extension, repo.id]
  );

  const handleTabChange = (type: SearchType) => {
    setSearchType(type);
    if (query.trim()) {
      handleSearch(type);
    }
  };

  const getMatchBadgeStyle = (matchType: string) => {
    switch (matchType) {
      case "semantic":
        return "bg-purple-950 text-purple-400 border-purple-800";
      case "keyword":
        return "bg-blue-950 text-blue-400 border-blue-800";
      case "symbol":
        return "bg-emerald-950 text-emerald-400 border-emerald-800";
      default:
        return "bg-amber-950 text-amber-400 border-amber-800";
    }
  };

  return (
    <div
      className="card animate-fade-in mt-6"
      style={{
        background: "var(--color-surface-overlay)",
        border: "1px solid var(--color-brand-800)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "var(--gradient-brand)" }}
          >
            <Compass size={20} className="text-white" />
          </div>
          <div>
            <h2 className="font-bold text-base text-gray-100">
              {repo.name} — Codebase Search Engine
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Multi-modal search: Reciprocal Rank Fusion (RRF), pgvector AI, & full-text match
            </p>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-200 rounded-lg hover:bg-gray-800"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Search Input Bar */}
      <div className="pt-4 space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="flex gap-2"
        >
          <div className="relative flex-1">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              className="input w-full pl-10 pr-4 py-2.5 text-sm rounded-xl bg-gray-900/80 border-gray-800 focus:border-blue-500 text-gray-100 placeholder-gray-500"
              placeholder="Search code, functions, classes, or ask a question..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={searching || !query.trim()}
            className="btn btn-primary px-5 py-2.5 text-xs font-semibold flex items-center gap-2"
          >
            {searching ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Sparkles size={14} />
            )}
            Search
          </button>
        </form>

        {/* Modality Tabs & Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-b border-gray-800/80 pb-3">
          <div className="flex items-center gap-1.5 bg-gray-900/60 p-1 rounded-xl border border-gray-800">
            {(
              [
                { id: "hybrid", label: "Hybrid RRF", icon: Layers },
                { id: "semantic", label: "Semantic AI", icon: Sparkles },
                { id: "keyword", label: "Keyword Text", icon: Code2 },
                { id: "symbol", label: "Symbols", icon: Hash },
              ] as const
            ).map((tab) => {
              const Icon = tab.icon;
              const active = searchType === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                    active
                      ? "bg-blue-600 text-white shadow-sm font-semibold"
                      : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                  }`}
                >
                  <Icon size={13} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Quick Language / Extension Filter */}
          <div className="flex items-center gap-2 text-xs">
            <Filter size={13} className="text-gray-500" />
            <input
              type="text"
              placeholder="Lang (e.g. Python)"
              className="px-2.5 py-1 rounded-lg bg-gray-900 border border-gray-800 text-gray-300 w-32 placeholder-gray-600 focus:outline-none focus:border-blue-500"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            />
            <input
              type="text"
              placeholder="Ext (e.g. .py)"
              className="px-2.5 py-1 rounded-lg bg-gray-900 border border-gray-800 text-gray-300 w-24 placeholder-gray-600 focus:outline-none focus:border-blue-500"
              value={extension}
              onChange={(e) => setExtension(e.target.value)}
            />
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="p-3 rounded-xl bg-red-950/40 border border-red-800 text-red-400 text-xs">
            {error}
          </div>
        )}

        {/* Results List */}
        {searching ? (
          <div className="py-12 flex flex-col items-center justify-center gap-2 text-gray-400 text-sm">
            <Loader2 size={24} className="animate-spin text-blue-500" />
            <span>Searching codebase using {searchType} algorithm…</span>
          </div>
        ) : response ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-gray-400 px-1">
              <span>
                Found <strong className="text-gray-200">{response.total_hits}</strong> results
                for &quot;{response.query}&quot;
              </span>
              <span className="font-mono text-gray-500">
                {response.duration_ms}ms execution time
              </span>
            </div>

            {response.results.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-xs rounded-xl bg-gray-900/40 border border-gray-800">
                No matching code chunks found for &quot;{response.query}&quot;. Try adjusting your query or filters.
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {response.results.map((hit: SearchResultItem, idx: number) => (
                  <div
                    key={`${hit.file_id}-${hit.start_line}-${idx}`}
                    className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800 hover:border-gray-700 transition-all space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 font-mono text-gray-300 truncate">
                        <FileCode2 size={14} className="text-blue-400 shrink-0" />
                        <span className="truncate">{hit.relative_path}</span>
                        <span className="text-gray-500">
                          L{hit.start_line}-{hit.end_line}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-md font-mono border ${getMatchBadgeStyle(
                            hit.match_type
                          )}`}
                        >
                          {hit.match_type.toUpperCase()}
                        </span>
                        <span className="text-xs font-semibold font-mono text-blue-400">
                          {Math.round(hit.score * 100)}% Match
                        </span>
                      </div>
                    </div>

                    <pre className="p-3 rounded-lg bg-gray-950/80 border border-gray-800 text-[11px] font-mono text-gray-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {hit.chunk_text}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="py-10 text-center text-gray-500 text-xs">
            Enter a search query above to search code symbols, functions, or natural language prompts.
          </div>
        )}
      </div>
    </div>
  );
}
