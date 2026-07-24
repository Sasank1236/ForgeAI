"use client";

import { useState, useEffect, useCallback } from "react";
import {
  GitBranch,
  FolderOpen,
  Loader2,
  AlertCircle,
  Trash2,
  RefreshCw,
  Clock,
  FileCode2,
  Files,
  HardDrive,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Plus,
  GitCommit,
  Globe,
} from "lucide-react";
import {
  importRepository,
  listRepositories,
  deleteRepository,
} from "@/lib/api";
import type { RepositoryListItem, ImportResponse } from "@/types/repository";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

// Language colour palette (deterministic by index)
const LANG_COLORS = [
  "hsl(220, 80%, 62%)",
  "hsl(265, 86%, 62%)",
  "hsl(142, 72%, 44%)",
  "hsl(38, 92%, 52%)",
  "hsl(200, 88%, 52%)",
  "hsl(355, 80%, 58%)",
  "hsl(30, 90%, 55%)",
  "hsl(180, 70%, 42%)",
];

function getLangColor(index: number): string {
  return LANG_COLORS[index % LANG_COLORS.length];
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config = {
    ready: {
      icon: CheckCircle2,
      label: "Ready",
      color: "var(--color-success)",
      bg: "hsl(142, 72%, 44%, 0.12)",
      border: "hsl(142, 72%, 44%, 0.3)",
    },
    scanning: {
      icon: Loader2,
      label: "Scanning…",
      color: "var(--color-info)",
      bg: "hsl(200, 88%, 52%, 0.12)",
      border: "hsl(200, 88%, 52%, 0.3)",
    },
    pending: {
      icon: Clock,
      label: "Pending",
      color: "var(--color-warning)",
      bg: "hsl(38, 92%, 52%, 0.12)",
      border: "hsl(38, 92%, 52%, 0.3)",
    },
    error: {
      icon: XCircle,
      label: "Error",
      color: "var(--color-danger)",
      bg: "hsl(355, 80%, 58%, 0.12)",
      border: "hsl(355, 80%, 58%, 0.3)",
    },
  }[status] ?? {
    icon: Clock,
    label: status,
    color: "var(--color-text-muted)",
    bg: "var(--color-surface-overlay)",
    border: "var(--color-border-default)",
  };

  const Icon = config.icon;
  const spin = status === "scanning";

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{
        color: config.color,
        background: config.bg,
        border: `1px solid ${config.border}`,
      }}
    >
      <Icon size={11} className={spin ? "animate-spin" : ""} />
      {config.label}
    </span>
  );
}

// ── Language bar ──────────────────────────────────────────────────────────────

function LanguageBar({
  languages,
  total,
}: {
  languages: Record<string, number>;
  total: number;
}) {
  const entries = Object.entries(languages).slice(0, 6);
  if (entries.length === 0 || total === 0) return null;

  return (
    <div className="space-y-2">
      {/* Stacked bar */}
      <div className="flex h-1.5 rounded-full overflow-hidden gap-px">
        {entries.map(([lang, count], i) => (
          <div
            key={lang}
            style={{
              width: `${((count / total) * 100).toFixed(1)}%`,
              background: getLangColor(i),
              borderRadius: "2px",
            }}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {entries.map(([lang, count], i) => (
          <span
            key={lang}
            className="flex items-center gap-1 text-xs"
            style={{ color: "var(--color-text-secondary)" }}
          >
            <span
              className="inline-block w-2 h-2 rounded-full shrink-0"
              style={{ background: getLangColor(i) }}
            />
            {lang}
            <span style={{ color: "var(--color-text-muted)" }}>{count}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Repository card ───────────────────────────────────────────────────────────

function RepoCard({
  repo,
  onDelete,
  deleting,
}: {
  repo: RepositoryListItem;
  onDelete: (id: string) => void;
  deleting: boolean;
}) {
  const stats = repo.stats;
  const langTotal = stats
    ? Object.values(stats.languages).reduce((a, b) => a + b, 0)
    : 0;

  return (
    <article
      className="card animate-fade-in-up"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
            style={{
              background: "hsl(220, 80%, 52%, 0.12)",
              border: "1px solid hsl(220, 80%, 52%, 0.25)",
            }}
          >
            <GitBranch size={16} style={{ color: "var(--color-brand-400)" }} />
          </div>
          <div className="min-w-0">
            <h3
              className="font-semibold truncate"
              style={{ color: "var(--color-text-primary)", fontSize: "14px" }}
            >
              {repo.name}
            </h3>
            <p
              className="text-xs mt-0.5 truncate font-mono"
              style={{ color: "var(--color-text-muted)" }}
              title={repo.root_path}
            >
              {repo.root_path}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={repo.status} />
          <button
            id={`delete-repo-${repo.id}`}
            onClick={() => onDelete(repo.id)}
            disabled={deleting}
            className="btn btn-ghost p-1.5 rounded-lg"
            title="Delete repository"
            aria-label={`Delete ${repo.name}`}
            style={{ color: "var(--color-danger)" }}
          >
            {deleting ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Trash2 size={14} />
            )}
          </button>
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div
          className="grid grid-cols-3 gap-3 px-3 py-2.5 rounded-lg"
          style={{ background: "var(--color-surface-base)" }}
        >
          <div className="text-center">
            <div
              className="text-base font-bold"
              style={{ color: "var(--color-text-primary)" }}
            >
              {stats.total_files.toLocaleString()}
            </div>
            <div
              className="text-[11px] mt-0.5 flex items-center justify-center gap-1"
              style={{ color: "var(--color-text-muted)" }}
            >
              <Files size={10} />
              Total files
            </div>
          </div>
          <div className="text-center">
            <div
              className="text-base font-bold"
              style={{ color: "var(--color-brand-400)" }}
            >
              {stats.code_files.toLocaleString()}
            </div>
            <div
              className="text-[11px] mt-0.5 flex items-center justify-center gap-1"
              style={{ color: "var(--color-text-muted)" }}
            >
              <FileCode2 size={10} />
              Code files
            </div>
          </div>
          <div className="text-center">
            <div
              className="text-base font-bold"
              style={{ color: "var(--color-text-primary)" }}
            >
              {formatBytes(stats.total_size_bytes)}
            </div>
            <div
              className="text-[11px] mt-0.5 flex items-center justify-center gap-1"
              style={{ color: "var(--color-text-muted)" }}
            >
              <HardDrive size={10} />
              Total size
            </div>
          </div>
        </div>
      )}

      {/* Language bar */}
      {stats && Object.keys(stats.languages).length > 0 && (
        <LanguageBar languages={stats.languages} total={langTotal} />
      )}

      {/* Footer */}
      <div
        className="flex items-center justify-between text-xs pt-1"
        style={{
          color: "var(--color-text-muted)",
          borderTop: "1px solid var(--color-border-muted)",
          paddingTop: "12px",
        }}
      >
        <span className="flex items-center gap-1.5">
          <Clock size={11} />
          {formatDate(repo.last_scanned)}
        </span>
        <span
          className="flex items-center gap-1"
          style={{ color: "var(--color-text-disabled)" }}
        >
          <RefreshCw size={10} />
          v{repo.scan_version}
        </span>
      </div>
    </article>
  );
}

// ── Import panel ──────────────────────────────────────────────────────────────

function ImportPanel({
  onSuccess,
}: {
  onSuccess: (res: ImportResponse) => void;
}) {
  const [path, setPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResponse | null>(null);

  const handleImport = async () => {
    if (!path.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await importRepository(path.trim());
      setResult(res);
      setPath("");
      onSuccess(res);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Import failed — check server logs.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading) handleImport();
  };

  return (
    <section
      className="card animate-fade-in"
      style={{
        background:
          "linear-gradient(135deg, hsl(222,18%,11%) 0%, hsl(222,18%,9%) 100%)",
        border: "1px solid var(--color-brand-800)",
      }}
    >
      {/* Section header */}
      <div className="flex items-center gap-3 mb-5">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: "var(--gradient-brand)" }}
        >
          <FolderOpen size={16} style={{ color: "white" }} />
        </div>
        <div>
          <h2
            className="font-semibold"
            style={{ color: "var(--color-text-primary)", fontSize: "15px" }}
          >
            Import Repository
          </h2>
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            Enter the absolute path to a local directory
          </p>
        </div>
      </div>

      {/* Input row */}
      <div className="flex gap-3">
        <input
          id="repo-path-input"
          type="text"
          className="input flex-1 font-mono text-sm"
          placeholder="C:/Users/dev/my-project  or  /home/dev/my-project"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          aria-label="Repository path"
        />
        <button
          id="import-repo-btn"
          className="btn btn-primary px-5"
          onClick={handleImport}
          disabled={loading || !path.trim()}
        >
          {loading ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              Scanning…
            </>
          ) : (
            <>
              <Plus size={15} />
              Import
            </>
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          className="flex items-start gap-2 mt-4 px-4 py-3 rounded-lg text-sm"
          style={{
            background: "hsl(355, 80%, 58%, 0.1)",
            border: "1px solid hsl(355, 80%, 58%, 0.3)",
            color: "var(--color-danger)",
          }}
        >
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          {error}
        </div>
      )}

      {/* Success result */}
      {result && (
        <div
          className="mt-4 px-4 py-3 rounded-lg text-sm"
          style={{
            background: "hsl(142, 72%, 44%, 0.1)",
            border: "1px solid hsl(142, 72%, 44%, 0.3)",
          }}
        >
          <div
            className="flex items-center gap-2 font-semibold mb-2"
            style={{ color: "var(--color-success)" }}
          >
            <CheckCircle2 size={15} />
            Scan complete in {formatMs(result.scan_time_ms)}
          </div>
          <div
            className="grid grid-cols-2 gap-2 text-xs"
            style={{ color: "var(--color-text-secondary)" }}
          >
            <span>
              <Files size={10} className="inline mr-1" />
              {result.files_scanned.toLocaleString()} files scanned
            </span>
            <span>
              {Object.keys(result.languages).length} languages detected
            </span>
          </div>
        </div>
      )}
    </section>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center py-20 text-center"
      aria-label="No repositories yet"
    >
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
        style={{
          background: "var(--color-surface-overlay)",
          border: "1px solid var(--color-border-default)",
        }}
      >
        <GitBranch size={28} style={{ color: "var(--color-text-disabled)" }} />
      </div>
      <h3
        className="font-semibold mb-2"
        style={{ color: "var(--color-text-primary)" }}
      >
        No repositories yet
      </h3>
      <p className="text-sm max-w-xs" style={{ color: "var(--color-text-muted)" }}>
        Import a local repository above to start scanning, indexing, and
        exploring your codebase with ForgeAI.
      </p>
      <div
        className="flex items-center gap-2 mt-4 text-xs"
        style={{ color: "var(--color-text-disabled)" }}
      >
        <ChevronRight size={12} />
        Repository Import → Scanner → Database → Embeddings → Chat
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [repos, setRepos] = useState<RepositoryListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchRepos = useCallback(async () => {
    try {
      setFetchError(null);
      const data = await listRepositories();
      setRepos(data);
    } catch {
      setFetchError("Could not reach the backend. Is the server running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepos();
  }, [fetchRepos]);

  const handleImportSuccess = useCallback(async (_res: ImportResponse) => {
    await fetchRepos();
  }, [fetchRepos]);

  const handleDelete = useCallback(
    async (id: string) => {
      const repo = repos.find((r) => r.id === id);
      if (!confirm(`Delete "${repo?.name ?? id}"? This cannot be undone.`)) return;
      setDeletingId(id);
      try {
        await deleteRepository(id);
        setRepos((prev) => prev.filter((r) => r.id !== id));
      } catch {
        alert("Delete failed — check server logs.");
      } finally {
        setDeletingId(null);
      }
    },
    [repos]
  );

  return (
    <div className="px-8 py-8 max-w-6xl mx-auto">
      {/* ── Page header ─────────────────────────────────────────────────── */}
      <header className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1
              className="text-2xl font-bold tracking-tight"
              style={{ color: "var(--color-text-primary)" }}
            >
              Repositories
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--color-text-muted)" }}>
              {repos.length === 0
                ? "Import your first repository to get started."
                : `${repos.length} repositor${repos.length === 1 ? "y" : "ies"} imported`}
            </p>
          </div>

          <button
            id="refresh-repos-btn"
            className="btn btn-secondary text-xs px-3 py-2"
            onClick={fetchRepos}
            disabled={loading}
            aria-label="Refresh repository list"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </header>

      {/* ── Import panel ─────────────────────────────────────────────────── */}
      <div className="mb-8">
        <ImportPanel onSuccess={handleImportSuccess} />
      </div>

      {/* ── Repository list ──────────────────────────────────────────────── */}
      {fetchError ? (
        <div
          className="flex items-center gap-3 px-5 py-4 rounded-xl text-sm"
          style={{
            background: "hsl(355, 80%, 58%, 0.08)",
            border: "1px solid hsl(355, 80%, 58%, 0.25)",
            color: "var(--color-danger)",
          }}
        >
          <AlertCircle size={16} />
          {fetchError}
        </div>
      ) : loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {[1, 2, 3].map((n) => (
            <div key={n} className="card">
              <div className="skeleton h-5 w-32 mb-3 rounded" />
              <div className="skeleton h-3 w-48 mb-5 rounded" />
              <div className="skeleton h-14 rounded-lg mb-4" />
              <div className="skeleton h-2 rounded-full mb-3" />
              <div className="skeleton h-3 w-24 rounded" />
            </div>
          ))}
        </div>
      ) : repos.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {/* Summary bar */}
          <div
            className="flex items-center gap-6 px-5 py-3 rounded-xl mb-5 text-sm"
            style={{
              background: "var(--color-surface-overlay)",
              border: "1px solid var(--color-border-default)",
            }}
          >
            <span
              className="flex items-center gap-2"
              style={{ color: "var(--color-text-secondary)" }}
            >
              <GitBranch size={13} style={{ color: "var(--color-brand-400)" }} />
              <strong style={{ color: "var(--color-text-primary)" }}>
                {repos.length}
              </strong>{" "}
              repos
            </span>
            <span
              className="flex items-center gap-2"
              style={{ color: "var(--color-text-secondary)" }}
            >
              <Files size={13} style={{ color: "var(--color-brand-400)" }} />
              <strong style={{ color: "var(--color-text-primary)" }}>
                {repos
                  .reduce((a, r) => a + (r.stats?.total_files ?? 0), 0)
                  .toLocaleString()}
              </strong>{" "}
              files total
            </span>
            <span
              className="flex items-center gap-2"
              style={{ color: "var(--color-text-secondary)" }}
            >
              <HardDrive size={13} style={{ color: "var(--color-brand-400)" }} />
              <strong style={{ color: "var(--color-text-primary)" }}>
                {formatBytes(
                  repos.reduce(
                    (a, r) => a + (r.stats?.total_size_bytes ?? 0),
                    0
                  )
                )}
              </strong>{" "}
              total size
            </span>
          </div>

          {/* Cards grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 stagger-children">
            {repos.map((repo) => (
              <RepoCard
                key={repo.id}
                repo={repo}
                onDelete={handleDelete}
                deleting={deletingId === repo.id}
              />
            ))}
          </div>

          {/* Git info sidebar note */}
          {repos.some((r) => r.status === "ready") && (
            <div
              className="flex items-start gap-3 mt-8 px-5 py-4 rounded-xl text-sm"
              style={{
                background: "var(--color-surface-overlay)",
                border: "1px solid var(--color-border-muted)",
              }}
            >
              <div className="flex gap-4 flex-wrap">
                <span
                  className="flex items-center gap-1.5"
                  style={{ color: "var(--color-text-muted)", fontSize: "12px" }}
                >
                  <GitCommit size={12} />
                  Git metadata auto-detected on import
                </span>
                <span
                  className="flex items-center gap-1.5"
                  style={{ color: "var(--color-text-muted)", fontSize: "12px" }}
                >
                  <Globe size={12} />
                  Re-import a path to trigger a rescan (version increments)
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
