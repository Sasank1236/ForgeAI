import type { Metadata } from "next";
import Link from "next/link";
import {
  GitBranch,
  BarChart3,
  Search,
  MessageSquare,
  Zap,
  FileCode,
  Home,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "ForgeAI repository dashboard — manage imported codebases.",
};

const navItems = [
  { href: "/", icon: Home, label: "Home" },
  { href: "/dashboard", icon: GitBranch, label: "Repositories" },
  { href: "/dashboard/search", icon: Search, label: "Search", soon: true },
  { href: "/dashboard/chat", icon: MessageSquare, label: "Chat", soon: true },
  { href: "/dashboard/plan", icon: Zap, label: "Planner", soon: true },
  { href: "/dashboard/code", icon: FileCode, label: "Code", soon: true },
  { href: "/dashboard/stats", icon: BarChart3, label: "Stats", soon: true },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full min-h-screen">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside
        className="fixed top-0 left-0 h-full w-56 flex flex-col z-40"
        style={{
          background: "var(--color-surface-raised)",
          borderRight: "1px solid var(--color-border-default)",
        }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-2.5 px-5 py-5"
          style={{ borderBottom: "1px solid var(--color-border-muted)" }}
        >
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "var(--gradient-brand)" }}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
              <path
                d="M3 4L10 2L17 4V10C17 14.4 13.4 17.4 10 18C6.6 17.4 3 14.4 3 10V4Z"
                stroke="white"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <path
                d="M7 10L9 12L13 8"
                stroke="white"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            className="font-bold text-sm"
            style={{ color: "var(--color-text-primary)" }}
          >
            ForgeAI
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ href, icon: Icon, label, soon }) => (
            <Link
              key={label}
              href={soon ? "#" : href}
              id={`nav-${label.toLowerCase()}`}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150"
              style={
                {
                  color: soon
                    ? "var(--color-text-disabled)"
                    : "var(--color-text-secondary)",
                  "--hover-bg": "var(--color-surface-overlay)",
                } as React.CSSProperties
              }
              onClick={soon ? (e) => e.preventDefault() : undefined}
            >
              <Icon size={15} />
              <span className="flex-1">{label}</span>
              {soon && (
                <span
                  className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
                  style={{
                    background: "var(--color-surface-overlay)",
                    color: "var(--color-text-disabled)",
                    border: "1px solid var(--color-border-muted)",
                  }}
                >
                  Soon
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* Version footer */}
        <div
          className="px-5 py-4"
          style={{ borderTop: "1px solid var(--color-border-muted)" }}
        >
          <p
            className="text-xs"
            style={{ color: "var(--color-text-disabled)" }}
          >
            Phase 2 — Repository Import
          </p>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="flex-1 ml-56 min-h-screen overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
