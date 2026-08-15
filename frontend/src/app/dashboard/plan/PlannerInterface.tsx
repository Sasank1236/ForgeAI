"use client";

import { useState, useEffect } from "react";
import {
  Zap,
  Trash2,
  Loader2,
  FileCode2,
  CheckCircle2,
  AlertTriangle,
  Code2,
  Sparkles,
  Layers,
  Wand2,
  Copy,
  Check,
} from "lucide-react";
import {
  createTaskPlan,
  deleteTaskPlan,
  generateCodeSuggestion,
  getTaskPlan,
  listRepositories,
  listTaskPlans,
} from "@/lib/api";
import type { RepositoryListItem } from "@/types/repository";
import type {
  CodeSuggestionResponse,
  TaskPlanResponse,
} from "@/types/plan";

export function PlannerInterface() {
  const [repos, setRepos] = useState<RepositoryListItem[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [plans, setPlans] = useState<TaskPlanResponse[]>([]);
  const [activePlanId, setActivePlanId] = useState<string | null>(null);
  const [activePlan, setActivePlan] = useState<TaskPlanResponse | null>(null);
  const [goalInput, setGoalInput] = useState("");
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingPlans, setLoadingPlans] = useState(false);
  const [loadingActivePlan, setLoadingActivePlan] = useState(false);
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [suggestionModalFile, setSuggestionModalFile] = useState<string | null>(null);
  const [suggestionInstruction, setSuggestionInstruction] = useState("");
  const [generatingSuggestion, setGeneratingSuggestion] = useState(false);
  const [suggestionResult, setSuggestionResult] = useState<CodeSuggestionResponse | null>(null);
  const [copiedDiff, setCopiedDiff] = useState(false);

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

  // Fetch plans when selected repository changes
  useEffect(() => {
    if (!selectedRepoId) return;
    let isMounted = true;
    listTaskPlans(selectedRepoId)
      .then((res) => {
        if (isMounted) {
          setPlans(res.items);
          if (res.items.length > 0) {
            setActivePlanId(res.items[0].id);
          } else {
            setActivePlanId(null);
            setActivePlan(null);
          }
        }
      })
      .catch(() => {
        if (isMounted) setPlans([]);
      })
      .finally(() => {
        if (isMounted) setLoadingPlans(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedRepoId]);

  // Fetch details when active plan changes
  useEffect(() => {
    let isMounted = true;
    if (!activePlanId) {
      return;
    }
    getTaskPlan(activePlanId)
      .then((data) => {
        if (isMounted) setActivePlan(data);
      })
      .catch(() => {
        if (isMounted) setActivePlan(null);
      })
      .finally(() => {
        if (isMounted) setLoadingActivePlan(false);
      });
    return () => {
      isMounted = false;
    };
  }, [activePlanId]);

  // Generate new execution plan
  const handleGeneratePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalInput.trim() || !selectedRepoId || generatingPlan) return;
    setGeneratingPlan(true);
    try {
      const plan = await createTaskPlan(selectedRepoId, {
        goal_description: goalInput.trim(),
      });
      setPlans((prev) => [plan, ...prev]);
      setActivePlanId(plan.id);
      setActivePlan(plan);
      setGoalInput("");
    } catch {
      alert("Failed to generate task plan.");
    } finally {
      setGeneratingPlan(false);
    }
  };

  // Delete plan
  const handleDeletePlan = async (planId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this execution plan?")) return;
    try {
      await deleteTaskPlan(planId);
      setPlans((prev) => prev.filter((p) => p.id !== planId));
      if (activePlanId === planId) {
        const remaining = plans.filter((p) => p.id !== planId);
        setActivePlanId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch {
      alert("Failed to delete plan.");
    }
  };

  // Request targeted code suggestion
  const handleGenerateSuggestion = async () => {
    if (!suggestionModalFile || !suggestionInstruction.trim() || !selectedRepoId) return;
    setGeneratingSuggestion(true);
    setSuggestionResult(null);
    try {
      const result = await generateCodeSuggestion(selectedRepoId, {
        file_path: suggestionModalFile,
        instruction: suggestionInstruction.trim(),
      });
      setSuggestionResult(result);
    } catch {
      alert("Failed to generate code suggestion diff.");
    } finally {
      setGeneratingSuggestion(false);
    }
  };

  const copyDiffToClipboard = (diffText: string) => {
    navigator.clipboard.writeText(diffText);
    setCopiedDiff(true);
    setTimeout(() => setCopiedDiff(false), 2000);
  };

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-gray-950 text-gray-100">
      {/* ── Plans Sidebar ────────────────────────────────────────────────── */}
      <aside className="w-72 border-r border-gray-800 bg-gray-900/60 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Repository
            </span>
            <span className="text-[11px] text-purple-400 font-mono flex items-center gap-1">
              <Zap size={12} />
              AI Planner
            </span>
          </div>

          <select
            className="w-full bg-gray-900 border border-gray-800 rounded-lg text-xs p-2 text-gray-200 focus:outline-none focus:border-purple-500"
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

        {/* Saved Plans List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingPlans ? (
            <div className="py-8 flex justify-center text-gray-500">
              <Loader2 size={16} className="animate-spin" />
            </div>
          ) : plans.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-500">
              No saved plans yet. Decompose a goal to start.
            </div>
          ) : (
            plans.map((p) => {
              const isActive = activePlanId === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setActivePlanId(p.id)}
                  className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                    isActive
                      ? "bg-purple-600/20 text-purple-400 font-medium border border-purple-800/60"
                      : "text-gray-300 hover:bg-gray-800/60 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <Layers size={13} className="shrink-0 text-purple-400" />
                    <span className="truncate">{p.title}</span>
                  </div>
                  <button
                    onClick={(e) => handleDeletePlan(p.id, e)}
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

      {/* ── Main Planner Area ────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-gray-950">
        {/* Goal Input Header */}
        <div className="p-4 sm:p-6 border-b border-gray-800 bg-gray-900/40">
          <form onSubmit={handleGeneratePlan} className="space-y-3 max-w-4xl">
            <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles size={14} className="text-purple-400" />
              Decompose Engineering Goal into Execution Plan
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                placeholder="e.g. Add JWT refresh token rotation to authentication router..."
                disabled={generatingPlan || !selectedRepoId}
                className="flex-1 input bg-gray-900 border-gray-800 text-xs sm:text-sm text-gray-100 placeholder-gray-500 rounded-xl py-3 px-4 focus:border-purple-500"
              />
              <button
                type="submit"
                disabled={generatingPlan || !goalInput.trim() || !selectedRepoId}
                className="btn btn-primary px-5 py-3 rounded-xl text-xs sm:text-sm flex items-center gap-2 shrink-0 bg-purple-600 hover:bg-purple-500 border-purple-600"
              >
                {generatingPlan ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Wand2 size={16} />
                )}
                <span>{generatingPlan ? "Decomposing..." : "Decompose Goal"}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Execution Plan View */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {loadingActivePlan ? (
            <div className="py-16 flex flex-col items-center justify-center text-gray-500 gap-2 text-xs">
              <Loader2 size={20} className="animate-spin text-purple-500" />
              <span>Loading task execution plan details…</span>
            </div>
          ) : !activePlan ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 max-w-lg mx-auto">
              <div className="w-12 h-12 rounded-2xl bg-purple-950 border border-purple-800 flex items-center justify-center text-purple-400">
                <Zap size={24} />
              </div>
              <h3 className="font-bold text-lg text-gray-100">
                AI Task Decomposition Engine
              </h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Describe any feature request, architectural refactoring, or bugfix above.
                ForgeAI will analyze codebase AST symbols and vector embeddings to construct a step-by-step execution plan with target file paths and code diff suggestions.
              </p>
            </div>
          ) : (
            <div className="space-y-6 max-w-4xl mx-auto">
              {/* Plan Summary Card */}
              <div className="p-5 rounded-2xl bg-gray-900/80 border border-gray-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-base sm:text-lg font-bold text-gray-100 flex items-center gap-2">
                    <Layers size={18} className="text-purple-400" />
                    {activePlan.title}
                  </h2>
                  <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase bg-purple-950 text-purple-400 border border-purple-800">
                    {activePlan.status}
                  </span>
                </div>

                <p className="text-xs text-gray-300 leading-relaxed">
                  <span className="text-gray-500 font-semibold">Goal: </span>
                  {activePlan.goal_description}
                </p>

                {activePlan.impact_summary && (
                  <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-900/50 text-amber-200 text-xs flex items-start gap-2">
                    <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />
                    <span>{activePlan.impact_summary}</span>
                  </div>
                )}
              </div>

              {/* Execution Steps List */}
              <div className="space-y-4">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-emerald-400" />
                  Step-by-Step Execution Plan ({activePlan.steps.length} Steps)
                </h3>

                {activePlan.steps.map((step) => (
                  <div
                    key={step.id}
                    className="p-5 rounded-2xl bg-gray-900/90 border border-gray-800 space-y-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <span className="w-7 h-7 rounded-lg bg-purple-950 border border-purple-800 text-purple-400 font-bold text-xs flex items-center justify-center">
                          {step.step_index}
                        </span>
                        <div>
                          <h4 className="text-sm font-bold text-gray-100">{step.title}</h4>
                          <p className="text-xs text-gray-400 mt-0.5">{step.description}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-1 rounded-lg bg-gray-950 border border-gray-800 text-[11px] font-mono text-blue-300 flex items-center gap-1.5">
                          <FileCode2 size={12} className="text-blue-400" />
                          {step.target_path}
                        </span>
                        <button
                          onClick={() => {
                            setSuggestionModalFile(step.target_path);
                            setSuggestionInstruction(`Implement step: ${step.title}`);
                            setSuggestionResult(null);
                          }}
                          className="btn btn-secondary text-xs px-2.5 py-1 flex items-center gap-1"
                        >
                          <Code2 size={12} />
                          Suggest Code
                        </button>
                      </div>
                    </div>

                    {/* Unified Diff Card */}
                    {step.code_diff && (
                      <div className="rounded-xl overflow-hidden bg-gray-950 border border-gray-800 text-xs font-mono">
                        <div className="p-2.5 bg-gray-900 border-b border-gray-800 flex items-center justify-between text-gray-400 text-[11px]">
                          <span>Suggested Code Diff ({step.target_path})</span>
                          <button
                            onClick={() => copyDiffToClipboard(step.code_diff || "")}
                            className="hover:text-gray-200 flex items-center gap-1"
                          >
                            {copiedDiff ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                            {copiedDiff ? "Copied" : "Copy Diff"}
                          </button>
                        </div>
                        <pre className="p-3 overflow-x-auto text-gray-300 leading-snug whitespace-pre-wrap">
                          {step.code_diff.split("\n").map((line, lIdx) => {
                            const isAdd = line.startsWith("+");
                            const isDel = line.startsWith("-");
                            return (
                              <div
                                key={lIdx}
                                className={
                                  isAdd
                                    ? "bg-emerald-950/40 text-emerald-300"
                                    : isDel
                                    ? "bg-red-950/40 text-red-400"
                                    : "text-gray-400"
                                }
                              >
                                {line}
                              </div>
                            );
                          })}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ── Code Suggestion Modal ────────────────────────────────────────── */}
      {suggestionModalFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-2xl bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-sm font-bold text-gray-100 flex items-center gap-2">
                <Code2 size={16} className="text-purple-400" />
                Generate Code Suggestion Diff ({suggestionModalFile})
              </h3>
              <button
                onClick={() => setSuggestionModalFile(null)}
                className="text-gray-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-300">Refactoring / Edit Instruction</label>
              <textarea
                value={suggestionInstruction}
                onChange={(e) => setSuggestionInstruction(e.target.value)}
                rows={3}
                className="w-full bg-gray-950 border border-gray-800 rounded-xl p-3 text-xs text-gray-100 focus:border-purple-500 focus:outline-none"
                placeholder="Specific instructions for refactoring or editing code..."
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setSuggestionModalFile(null)}
                className="btn btn-secondary text-xs px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateSuggestion}
                disabled={generatingSuggestion || !suggestionInstruction.trim()}
                className="btn btn-primary text-xs px-4 py-2 flex items-center gap-1.5 bg-purple-600 border-purple-600"
              >
                {generatingSuggestion ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                <span>{generatingSuggestion ? "Generating Diff..." : "Generate Suggestion"}</span>
              </button>
            </div>

            {/* Modal Result */}
            {suggestionResult && (
              <div className="pt-3 border-t border-gray-800 space-y-2 max-h-60 overflow-y-auto">
                <p className="text-xs text-purple-300 font-medium">{suggestionResult.explanation}</p>
                <div className="rounded-xl overflow-hidden bg-gray-950 border border-gray-800 text-[11px] font-mono p-3">
                  <pre className="whitespace-pre-wrap text-gray-300">{suggestionResult.diff}</pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
