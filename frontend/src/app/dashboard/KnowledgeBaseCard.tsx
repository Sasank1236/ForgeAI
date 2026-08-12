"use client";

import { useState, useEffect } from "react";
import {
  Database,
  Loader2,
  Sparkles,
  CheckCircle,
  AlertTriangle,
  Trash2,
  Cpu,
  Layers,
  FileText,
} from "lucide-react";
import { clearIndex, getIndexStats, indexRepository } from "@/lib/api";
import type { IndexResponse, IndexStatsResponse } from "@/types/embedding";
import type { RepositoryListItem } from "@/types/repository";

interface KnowledgeBaseCardProps {
  repo: RepositoryListItem;
  onClose?: () => void;
}

export function KnowledgeBaseCard({ repo, onClose }: KnowledgeBaseCardProps) {
  const [indexing, setIndexing] = useState(false);
  const [loadingStats, setLoadingStats] = useState(true);
  const [stats, setStats] = useState<IndexStatsResponse | null>(null);
  const [indexResult, setIndexResult] = useState<IndexResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    getIndexStats(repo.id)
      .then((data) => {
        if (isMounted) {
          setStats(data);
          setLoadingStats(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setStats(null);
          setLoadingStats(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [repo.id]);

  const handleRunIndexing = async (force = false) => {
    setIndexing(true);
    setError(null);
    try {
      const res = await indexRepository(repo.id, { force_reindex: force });
      setIndexResult(res);
      setStats(res.stats);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Knowledge base vector indexing failed.";
      setError(msg);
    } finally {
      setIndexing(false);
    }
  };

  const handleClearIndex = async () => {
    if (!confirm(`Clear vector embeddings for ${repo.name}?`)) return;
    try {
      await clearIndex(repo.id);
      setStats({
        total_chunks: 0,
        total_embedded_files: 0,
        total_tokens: 0,
        duration_ms: 0,
        by_chunk_type: {},
      });
      setIndexResult(null);
    } catch {
      setError("Failed to clear vector index.");
    }
  };

  const hasChunks = (stats?.total_chunks ?? 0) > 0;

  return (
    <div
      className="card animate-fade-in mt-6"
      style={{
        background: "var(--color-surface-overlay)",
        border: "1px solid var(--color-brand-800)",
      }}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "var(--gradient-brand)" }}
          >
            <Database size={20} className="text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-base text-gray-100">
                {repo.name} — Vector Knowledge Base
              </h2>
              <span
                className={`text-xs px-2 py-0.5 rounded-md font-mono border ${
                  hasChunks
                    ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                    : "bg-amber-950 text-amber-400 border-amber-800"
                }`}
              >
                {hasChunks ? "Indexed (1536-dim)" : "Unindexed"}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              OpenAI text-embedding-3-small vector chunks for semantic code search
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            className="btn btn-primary text-xs px-3 py-1.5"
            onClick={() => handleRunIndexing(false)}
            disabled={indexing}
          >
            {indexing ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                Embedding Chunks…
              </>
            ) : (
              <>
                <Sparkles size={13} />
                {hasChunks ? "Update Index" : "Index Knowledge Base"}
              </>
            )}
          </button>

          {hasChunks && (
            <button
              className="btn btn-secondary text-xs px-3 py-1.5 text-red-400 hover:text-red-300"
              onClick={handleClearIndex}
              disabled={indexing}
              title="Clear vector index"
            >
              <Trash2 size={13} />
            </button>
          )}

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

      {/* Body Stats */}
      <div className="pt-4 space-y-4">
        {loadingStats ? (
          <div className="py-8 flex justify-center items-center text-gray-400 gap-2 text-sm">
            <Loader2 size={16} className="animate-spin text-blue-500" />
            Loading vector statistics...
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800">
              <span className="text-gray-400 block mb-1 flex items-center gap-1">
                <Layers size={12} className="text-blue-400" /> Total Chunks
              </span>
              <strong className="text-lg font-bold text-gray-100">
                {stats?.total_chunks.toLocaleString() ?? 0}
              </strong>
            </div>

            <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800">
              <span className="text-gray-400 block mb-1 flex items-center gap-1">
                <FileText size={12} className="text-emerald-400" /> Embedded Files
              </span>
              <strong className="text-lg font-bold text-emerald-400">
                {stats?.total_embedded_files.toLocaleString() ?? 0}
              </strong>
            </div>

            <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800">
              <span className="text-gray-400 block mb-1 flex items-center gap-1">
                <Cpu size={12} className="text-purple-400" /> Total Tokens
              </span>
              <strong className="text-lg font-bold text-purple-400">
                {stats?.total_tokens.toLocaleString() ?? 0}
              </strong>
            </div>

            <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800">
              <span className="text-gray-400 block mb-1 flex items-center gap-1">
                <Sparkles size={12} className="text-amber-400" /> Vector Model
              </span>
              <strong className="text-xs font-mono text-gray-200 block truncate">
                text-embedding-3-small
              </strong>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="p-3 rounded-xl bg-red-950/40 border border-red-800 text-red-400 text-xs flex items-center gap-2">
            <AlertTriangle size={15} />
            {error}
          </div>
        )}

        {/* Success Execution Result */}
        {indexResult && (
          <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/60 space-y-2 text-xs">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <CheckCircle size={16} />
              Vector Indexing Completed in {indexResult.stats.duration_ms}ms
            </div>
            <p className="text-gray-300">
              Generated {indexResult.stats.total_chunks} vector chunk embeddings across{" "}
              {indexResult.stats.total_embedded_files} files using 1536-dimensional pgvector representations.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
