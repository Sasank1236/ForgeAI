import Link from "next/link";
import type { Metadata } from "next";
import {
  GitBranch,
  Search,
  MessageSquare,
  Zap,
  FileCode,
  BarChart3,
  ChevronRight,
  Cpu,
  Database,
  Network,
} from "lucide-react";

export const metadata: Metadata = {
  title: "ForgeAI — Repository-Aware AI Coding Assistant",
};

// ─── Feature Data ─────────────────────────────────────────────────────────────
const features = [
  {
    icon: GitBranch,
    title: "Repository Import",
    description:
      "Point ForgeAI at any local repository. It scans, indexes, and builds a complete knowledge map of your entire codebase.",
    badge: "Core",
    color: "hsl(220, 80%, 52%)",
  },
  {
    icon: Search,
    title: "Intelligent Search",
    description:
      "Four search modes: semantic, keyword, symbol, and file. Ask natural language questions and find exactly what you need.",
    badge: "Core",
    color: "hsl(265, 86%, 62%)",
  },
  {
    icon: MessageSquare,
    title: "Repository Chat",
    description:
      "Ask anything about your codebase. ForgeAI retrieves relevant context automatically before every answer.",
    badge: "Core",
    color: "hsl(200, 88%, 52%)",
  },
  {
    icon: Zap,
    title: "Task Planner",
    description:
      "Describe a feature or bugfix. Get a structured, step-by-step implementation plan grounded in your actual code.",
    badge: "Core",
    color: "hsl(38, 92%, 52%)",
  },
  {
    icon: FileCode,
    title: "Code Suggestions",
    description:
      "AI-generated code hints and snippets tailored to your repository's patterns, conventions, and architecture.",
    badge: "Core",
    color: "hsl(142, 72%, 44%)",
  },
  {
    icon: BarChart3,
    title: "Project Dashboard",
    description:
      "Live overview of your repository: file count, language breakdown, symbol index, and dependency graph.",
    badge: "Core",
    color: "hsl(355, 80%, 58%)",
  },
];

const techStack = [
  { icon: Cpu, label: "GPT-4o", sublabel: "LLM Engine" },
  { icon: Database, label: "pgvector", sublabel: "Vector Search" },
  { icon: Network, label: "Tree-sitter", sublabel: "Code Parser" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function HomePage() {
  return (
    <main className="relative min-h-full flex flex-col items-center px-6 py-16 overflow-hidden">
      {/* Background grid */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-text-primary) 1px, transparent 1px), linear-gradient(90deg, var(--color-text-primary) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
        aria-hidden="true"
      />

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="relative z-10 flex flex-col items-center text-center max-w-4xl mx-auto animate-fade-in">
        {/* Wordmark */}
        <div className="flex items-center gap-3 mb-8">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{
              background: "var(--gradient-brand)",
              boxShadow: "var(--shadow-glow)",
            }}
            aria-hidden="true"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
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
            className="text-xl font-bold tracking-tight"
            style={{ color: "var(--color-text-primary)" }}
          >
            ForgeAI
          </span>
          <span
            className="badge badge-brand"
            style={{ fontSize: "10px" }}
          >
            v1.0
          </span>
        </div>

        {/* Headline */}
        <h1
          className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6"
          style={{ letterSpacing: "-0.03em" }}
        >
          <span style={{ color: "var(--color-text-primary)" }}>
            Understand your{" "}
          </span>
          <span className="gradient-text">codebase</span>
          <br />
          <span style={{ color: "var(--color-text-primary)" }}>
            before writing code
          </span>
        </h1>

        {/* Subtitle */}
        <p
          className="text-xl max-w-2xl mb-10 leading-relaxed"
          style={{ color: "var(--color-text-secondary)" }}
        >
          ForgeAI is a repository-aware AI assistant that indexes your entire
          project, retrieves precise context, and helps you search, plan, and
          implement — without hallucination.
        </p>

        {/* CTAs */}
        <div className="flex flex-wrap gap-4 justify-center mb-16">
          <Link
            href="/dashboard"
            id="cta-get-started"
            className="btn btn-primary text-base px-8 py-3"
          >
            Get Started
            <ChevronRight size={18} aria-hidden="true" />
          </Link>
          <a
            href="http://localhost:8000/docs"
            id="cta-api-docs"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary text-base px-8 py-3"
          >
            API Docs
          </a>
        </div>

        {/* Tech badges */}
        <div className="flex flex-wrap gap-6 justify-center">
          {techStack.map(({ icon: Icon, label, sublabel }) => (
            <div
              key={label}
              className="flex items-center gap-2.5 px-4 py-2 rounded-full"
              style={{
                background: "var(--color-surface-overlay)",
                border: "1px solid var(--color-border-default)",
              }}
            >
              <Icon
                size={14}
                style={{ color: "var(--color-brand-400)" }}
                aria-hidden="true"
              />
              <span
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "var(--color-text-primary)",
                }}
              >
                {label}
              </span>
              <span
                style={{
                  fontSize: "12px",
                  color: "var(--color-text-muted)",
                }}
              >
                {sublabel}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Divider */}
      <div className="divider w-full max-w-4xl my-20 z-10" aria-hidden="true" />

      {/* ── Features Grid ───────────────────────────────────────────────────── */}
      <section
        className="relative z-10 w-full max-w-6xl mx-auto"
        aria-labelledby="features-heading"
      >
        <div className="text-center mb-12">
          <h2
            id="features-heading"
            className="text-3xl font-bold mb-3"
          >
            Everything you need to understand a repository
          </h2>
          <p style={{ color: "var(--color-text-secondary)" }}>
            Six core capabilities, all grounded in real repository context.
          </p>
        </div>

        <div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 stagger-children"
        >
          {features.map(({ icon: Icon, title, description, badge, color }) => (
            <article
              key={title}
              className="card card-hover animate-fade-in-up"
            >
              {/* Icon */}
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                style={{
                  background: `${color}18`,
                  border: `1px solid ${color}30`,
                }}
              >
                <Icon size={18} style={{ color }} aria-hidden="true" />
              </div>

              {/* Header */}
              <div className="flex items-start justify-between gap-2 mb-3">
                <h3
                  className="font-semibold"
                  style={{
                    color: "var(--color-text-primary)",
                    fontSize: "15px",
                  }}
                >
                  {title}
                </h3>
                <span
                  className="badge badge-brand shrink-0"
                  style={{ fontSize: "9px" }}
                >
                  {badge}
                </span>
              </div>

              {/* Description */}
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "13.5px",
                  lineHeight: 1.65,
                }}
              >
                {description}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer
        className="relative z-10 mt-24 text-center"
        style={{ color: "var(--color-text-muted)", fontSize: "13px" }}
      >
        <p>
          ForgeAI v1.0 MVP &mdash; Built with FastAPI, Next.js, pgvector &amp; GPT-4o
        </p>
      </footer>
    </main>
  );
}
