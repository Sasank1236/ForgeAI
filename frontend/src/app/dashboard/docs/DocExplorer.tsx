"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  Loader2,
  Trash2,
  Download,
  Copy,
  Check,
  Wand2,
  Sparkles,
  BookOpen,
  Edit3,
  Save,
  FileCode,
  Layers,
  Code,
} from "lucide-react";
import {
  deleteDocumentation,
  generateDocumentation,
  listDocumentation,
  listRepositories,
  updateDocumentation,
} from "@/lib/api";
import type { RepositoryListItem } from "@/types/repository";
import type {
  DocType,
  DocumentationResponse,
} from "@/types/documentation";

const DOC_TYPES: { type: DocType; label: string; icon: typeof FileText } = [
  { type: "readme", label: "README.md", icon: FileText },
  { type: "architecture", label: "Architecture", icon: Layers },
  { type: "api_reference", label: "API Reference", icon: Code },
];

export function DocExplorer() {
  const [repos, setRepos] = useState<RepositoryListItem[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [selectedDocType, setSelectedDocType] = useState<DocType>("readme");
  const [docs, setDocs] = useState<DocumentationResponse[]>([]);
  const [activeDoc, setActiveDoc] = useState<DocumentationResponse | null>(null);
  const [customInstructions, setCustomInstructions] = useState("");
  const [editingContent, setEditingContent] = useState<string | null>(null);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

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

  // Fetch docs when selected repository changes
  useEffect(() => {
    if (!selectedRepoId) return;
    let isMounted = true;
    listDocumentation(selectedRepoId)
      .then((res) => {
        if (isMounted) {
          setDocs(res.items);
          const found = res.items.find((d) => d.doc_type === selectedDocType);
          setActiveDoc(found || null);
          setEditingContent(null);
        }
      })
      .catch(() => {
        if (isMounted) setDocs([]);
      })
      .finally(() => {
        if (isMounted) setLoadingDocs(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedRepoId, selectedDocType]);

  // Generate documentation
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId || generating) return;
    setGenerating(true);
    try {
      const newDoc = await generateDocumentation(selectedRepoId, {
        doc_type: selectedDocType,
        custom_instructions: customInstructions.trim() || undefined,
      });
      setDocs((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
      setActiveDoc(newDoc);
      setEditingContent(null);
      setCustomInstructions("");
    } catch {
      alert("Failed to generate documentation.");
    } finally {
      setGenerating(false);
    }
  };

  // Save edited content
  const handleSaveEdit = async () => {
    if (!activeDoc || editingContent === null) return;
    setSaving(true);
    try {
      const updated = await updateDocumentation(activeDoc.id, {
        content: editingContent,
      });
      setActiveDoc(updated);
      setEditingContent(null);
    } catch {
      alert("Failed to update documentation content.");
    } finally {
      setSaving(false);
    }
  };

  // Delete documentation
  const handleDelete = async (docId: string) => {
    if (!confirm("Delete this documentation record?")) return;
    try {
      await deleteDocumentation(docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
      if (activeDoc?.id === docId) {
        setActiveDoc(null);
        setEditingContent(null);
      }
    } catch {
      alert("Failed to delete documentation.");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadMarkdown = (title: string, content: string) => {
    const filename = `${title.toLowerCase().replace(/[^a-z0-9]/g, "_")}.md`;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-gray-950 text-gray-100">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="w-72 border-r border-gray-800 bg-gray-900/60 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Repository
            </span>
            <span className="text-[11px] text-blue-400 font-mono flex items-center gap-1">
              <BookOpen size={12} />
              Auto Docs
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
        </div>

        {/* Doc Types list */}
        <div className="p-3 border-b border-gray-800 space-y-1">
          <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider px-2">
            Document Types
          </span>
          {DOC_TYPES.map(({ type, label, icon: Icon }) => {
            const isSelected = selectedDocType === type;
            return (
              <button
                key={type}
                onClick={() => setSelectedDocType(type)}
                className={`w-full flex items-center justify-between p-2.5 rounded-lg text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-blue-600/20 text-blue-400 border border-blue-800/60"
                    : "text-gray-400 hover:bg-gray-800/60 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon size={14} className={isSelected ? "text-blue-400" : "text-gray-500"} />
                  <span>{label}</span>
                </div>
                {docs.some((d) => d.doc_type === type) && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                )}
              </button>
            );
          })}
        </div>

        {/* Generated History */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider px-2 py-1 block">
            Generated History
          </span>
          {loadingDocs ? (
            <div className="py-8 flex justify-center text-gray-500">
              <Loader2 size={16} className="animate-spin" />
            </div>
          ) : docs.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-500">
              No docs generated yet. Click &quot;Generate Documentation&quot; to synthesize.
            </div>
          ) : (
            docs.map((d) => {
              const isActive = activeDoc?.id === d.id;
              return (
                <div
                  key={d.id}
                  onClick={() => {
                    setActiveDoc(d);
                    setSelectedDocType(d.doc_type);
                    setEditingContent(null);
                  }}
                  className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                    isActive
                      ? "bg-gray-800 text-white font-medium border border-gray-700"
                      : "text-gray-400 hover:bg-gray-800/60 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileCode size={13} className="shrink-0 text-blue-400" />
                    <span className="truncate">{d.title}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(d.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-opacity"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* ── Main Documentation Area ──────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-gray-950">
        {/* Header Bar */}
        <div className="p-4 sm:p-5 border-b border-gray-800 bg-gray-900/40 flex items-center justify-between">
          <form onSubmit={handleGenerate} className="flex items-center gap-2 flex-1 max-w-2xl">
            <input
              type="text"
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder="Custom instructions (e.g. Focus on deployment guides & API routes)..."
              disabled={generating || !selectedRepoId}
              className="flex-1 input bg-gray-900 border-gray-800 text-xs text-gray-100 placeholder-gray-500 rounded-xl py-2.5 px-3 focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={generating || !selectedRepoId}
              className="btn btn-primary px-4 py-2.5 rounded-xl text-xs flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 border-blue-600 shrink-0"
            >
              {generating ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Wand2 size={14} />
              )}
              <span>{generating ? "Synthesizing..." : "Generate Docs"}</span>
            </button>
          </form>

          {activeDoc && (
            <div className="flex items-center gap-2 shrink-0">
              {editingContent !== null ? (
                <button
                  onClick={handleSaveEdit}
                  disabled={saving}
                  className="btn btn-primary text-xs px-3 py-2 flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 border-emerald-600"
                >
                  {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                  <span>Save</span>
                </button>
              ) : (
                <button
                  onClick={() => setEditingContent(activeDoc.content)}
                  className="btn btn-secondary text-xs px-3 py-2 flex items-center gap-1.5"
                >
                  <Edit3 size={13} />
                  <span>Edit</span>
                </button>
              )}

              <button
                onClick={() => copyToClipboard(editingContent ?? activeDoc.content)}
                className="btn btn-secondary text-xs px-3 py-2 flex items-center gap-1.5"
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>

              <button
                onClick={() => downloadMarkdown(activeDoc.title, editingContent ?? activeDoc.content)}
                className="btn btn-secondary text-xs px-3 py-2 flex items-center gap-1.5"
              >
                <Download size={13} />
                <span>Export .md</span>
              </button>
            </div>
          )}
        </div>

        {/* Content Viewer / Editor */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {!activeDoc && editingContent === null ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 max-w-lg mx-auto">
              <div className="w-12 h-12 rounded-2xl bg-blue-950 border border-blue-800 flex items-center justify-center text-blue-400">
                <Sparkles size={24} />
              </div>
              <h3 className="font-bold text-lg text-gray-100">
                Auto Technical Documentation Engine
              </h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                ForgeAI synthesizes production-ready Markdown documentation using extracted Tree-sitter AST symbols, module dependency graphs, and repository file structure.
              </p>
              <button
                onClick={handleGenerate}
                disabled={generating || !selectedRepoId}
                className="btn btn-primary px-5 py-2.5 rounded-xl text-xs flex items-center gap-2 bg-blue-600"
              >
                <Wand2 size={15} />
                <span>Generate {selectedDocType.toUpperCase()} Now</span>
              </button>
            </div>
          ) : editingContent !== null ? (
            <div className="max-w-4xl mx-auto space-y-3">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Markdown Editor
              </span>
              <textarea
                value={editingContent}
                onChange={(e) => setEditingContent(e.target.value)}
                rows={28}
                className="w-full bg-gray-900 border border-gray-800 rounded-2xl p-5 text-xs sm:text-sm font-mono text-gray-100 focus:border-blue-500 focus:outline-none leading-relaxed"
              />
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="p-6 rounded-2xl bg-gray-900/80 border border-gray-800 space-y-4">
                <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                  <h1 className="text-base sm:text-xl font-bold text-gray-100 flex items-center gap-2">
                    <BookOpen size={20} className="text-blue-400" />
                    {activeDoc?.title}
                  </h1>
                  {activeDoc?.file_path && (
                    <span className="px-2.5 py-1 rounded-lg bg-gray-950 border border-gray-800 text-[11px] font-mono text-blue-300">
                      {activeDoc.file_path}
                    </span>
                  )}
                </div>

                <div className="prose prose-invert max-w-none text-xs sm:text-sm leading-relaxed text-gray-200">
                  <pre className="whitespace-pre-wrap font-sans bg-transparent p-0 border-0">
                    {activeDoc?.content}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
