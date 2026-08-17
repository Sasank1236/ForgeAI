"use client";

import { useState, useEffect } from "react";
import {
  Activity,
  Database,
  HardDrive,
  Cpu,
  RefreshCw,
  Loader2,
  FileCode,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  GitBranch,
  MessageSquare,
  Zap,
  BookOpen,
} from "lucide-react";
import { getSystemHealth } from "@/lib/api";
import type { SystemHealthResponse } from "@/types/system";

export function StatsExplorer() {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const handleManualRefresh = () => {
    setRefreshing(true);
    getSystemHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setRefreshing(false));
  };

  useEffect(() => {
    let isMounted = true;
    getSystemHealth()
      .then((data) => {
        if (isMounted) setHealth(data);
      })
      .catch(() => {
        if (isMounted) setHealth(null);
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="h-[calc(100vh-64px)] overflow-y-auto bg-gray-950 text-gray-100 p-4 sm:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gray-900/80 border border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-2xl bg-blue-950 border border-blue-800 text-blue-400">
              <Activity size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-100 flex items-center gap-2">
                System Health & Database Telemetry
              </h1>
              <p className="text-xs text-gray-400 mt-0.5 font-mono">
                Real-time service readiness probes, host resource utilization & database statistics
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleManualRefresh}
              disabled={refreshing}
              className="btn btn-secondary text-xs px-3.5 py-2.5 rounded-xl flex items-center gap-2"
            >
              <RefreshCw size={14} className={refreshing ? "animate-spin text-blue-400" : ""} />
              <span>Refresh Metrics</span>
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-20 flex justify-center text-gray-500">
            <Loader2 size={24} className="animate-spin" />
          </div>
        ) : !health ? (
          <div className="p-8 text-center text-sm text-red-400 bg-red-950/20 border border-red-900 rounded-2xl">
            Failed to connect to system health telemetry endpoint.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Status overview cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Overall status */}
              <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-2">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
                  Overall System Status
                </span>
                <div className="flex items-center gap-2 pt-1">
                  {health.status === "ok" ? (
                    <CheckCircle2 size={20} className="text-emerald-400" />
                  ) : (
                    <AlertTriangle size={20} className="text-amber-400" />
                  )}
                  <span className="text-lg font-bold text-gray-100 uppercase tracking-wide">
                    {health.status}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-gray-400">
                  Env: <span className="text-blue-300">{health.environment}</span> • Python {health.python_version}
                </div>
              </div>

              {/* Database status */}
              <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-2">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block flex items-center gap-1.5">
                  <Database size={14} className="text-blue-400" />
                  PostgreSQL Database
                </span>
                <div className="flex items-center gap-2 pt-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-base font-bold text-gray-100 capitalize">
                    {health.database}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-gray-400">
                  Connection pool active
                </div>
              </div>

              {/* Cache status */}
              <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-2">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block flex items-center gap-1.5">
                  <Cpu size={14} className="text-blue-400" />
                  Redis Cache Status
                </span>
                <div className="flex items-center gap-2 pt-1">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      health.redis === "connected" ? "bg-emerald-400" : "bg-amber-400"
                    }`}
                  />
                  <span className="text-base font-bold text-gray-100 capitalize">
                    {health.redis}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-gray-400">
                  Response cache layer
                </div>
              </div>
            </div>

            {/* Host Disk & System metrics */}
            <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                <HardDrive size={16} className="text-blue-400" />
                Host Disk & System Storage
              </span>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-gray-400">Disk Space Usage</span>
                  <span className="text-gray-200 font-bold">
                    {health.system.disk_used_percent}% ({health.system.disk_free_gb} GB Free / {health.system.disk_total_gb} GB Total)
                  </span>
                </div>
                <div className="w-full h-3 rounded-full bg-gray-950 overflow-hidden p-0.5 border border-gray-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500"
                    style={{ width: `${Math.min(health.system.disk_used_percent, 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Database Telemetry Metrics Grid */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
                Indexed Database Telemetry
              </span>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <GitBranch size={14} className="text-blue-400" />
                    <span>Repositories</span>
                  </div>
                  <span className="text-xl font-bold font-mono text-gray-100">
                    {health.telemetry.repositories}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <FileCode size={14} className="text-blue-400" />
                    <span>Source Files</span>
                  </div>
                  <span className="text-xl font-bold font-mono text-gray-100">
                    {health.telemetry.files}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <Layers size={14} className="text-blue-400" />
                    <span>AST Symbols</span>
                  </div>
                  <span className="text-xl font-bold font-mono text-gray-100">
                    {health.telemetry.symbols}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <Sparkles size={14} className="text-blue-400" />
                    <span>Vector Chunks</span>
                  </div>
                  <span className="text-xl font-bold font-mono text-gray-100">
                    {health.telemetry.embeddings}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <MessageSquare size={14} className="text-blue-400" />
                    <span>Chat Sessions</span>
                  </div>
                  <span className="text-xl font-bold font-mono text-gray-100">
                    {health.telemetry.chat_sessions}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <Zap size={14} className="text-blue-400" />
                    <span>Task Plans</span>
                  </div>
                  <span className="text-xl font-bold font-mono text-gray-100">
                    {health.telemetry.task_plans}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1 sm:col-span-2">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <BookOpen size={14} className="text-blue-400" />
                    <span>Auto Documentation Files</span>
                  </div>
                  <span className="text-xl font-bold font-mono text-gray-100">
                    {health.telemetry.documentation_files}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
