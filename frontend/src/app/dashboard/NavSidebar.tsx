"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  GitBranch, BarChart3, Search, MessageSquare,
  Zap, FileCode, Home, ChevronLeft, ChevronRight,
  Menu, X,
} from "lucide-react";

// ── Constants ─────────────────────────────────────────────────────────────────
const EXPANDED_W = 220;
const COLLAPSED_W = 60;
const MOBILE_BP = 1024; // px — below this, sidebar becomes an overlay

const navItems = [
  { href: "/",               icon: Home,          label: "Home"         },
  { href: "/dashboard",      icon: GitBranch,     label: "Repositories" },
  { href: "/dashboard/search", icon: Search,      label: "Search",  soon: true },
  { href: "/dashboard/chat",   icon: MessageSquare, label: "Chat",   soon: true },
  { href: "/dashboard/plan",   icon: Zap,         label: "Planner", soon: true },
  { href: "/dashboard/code",   icon: FileCode,    label: "Code",    soon: true },
  { href: "/dashboard/stats",  icon: BarChart3,   label: "Stats",   soon: true },
];

// ── Shell ─────────────────────────────────────────────────────────────────────
export default function DashboardShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  // Desktop: sidebar expanded vs icon-only collapsed
  const [expanded, setExpanded] = useState(true);
  // Mobile: drawer open/closed
  const [mobileOpen, setMobileOpen] = useState(false);
  // Whether we're in mobile layout
  const [isMobile, setIsMobile] = useState(false);

  // ── Responsive detection ──────────────────────────────────────────────────
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < MOBILE_BP);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const [currentPath, setCurrentPath] = useState(pathname);
  if (currentPath !== pathname) {
    setCurrentPath(pathname);
    setMobileOpen(false);
  }

  // ── Keyboard shortcut: Ctrl+B ─────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "b") {
        e.preventDefault();
        if (isMobile) setMobileOpen((p) => !p);
        else setExpanded((p) => !p);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isMobile]);

  // ── Derived values ─────────────────────────────────────────────────────────
  const showLabels = isMobile ? true : expanded;
  const sidebarPx  = isMobile ? EXPANDED_W : (expanded ? EXPANDED_W : COLLAPSED_W);

  // ── Styles helpers ─────────────────────────────────────────────────────────
  const TRANSITION = "220ms cubic-bezier(0.4,0,0.2,1)";

  return (
    <div style={{ display: "flex", minHeight: "100vh", position: "relative" }}>

      {/* ── Mobile backdrop ─────────────────────────────────────────────── */}
      {isMobile && mobileOpen && (
        <div
          aria-hidden="true"
          onClick={() => setMobileOpen(false)}
          style={{
            position: "fixed", inset: 0, zIndex: 30,
            background: "rgba(0,0,0,0.55)",
            backdropFilter: "blur(3px)",
            WebkitBackdropFilter: "blur(3px)",
            transition: `opacity ${TRANSITION}`,
          }}
        />
      )}

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside
        aria-label="Main navigation"
        style={{
          position: "fixed",
          top: 0, left: 0, height: "100%",
          width: sidebarPx,
          zIndex: 40,
          display: "flex",
          flexDirection: "column",
          background: "var(--color-surface-raised)",
          borderRight: "1px solid var(--color-border-default)",
          overflowX: "hidden",
          transition: `width ${TRANSITION}, transform ${TRANSITION}`,
          // Mobile: slide in/out via transform
          transform: isMobile
            ? mobileOpen ? "translateX(0)" : `translateX(-${EXPANDED_W}px)`
            : "translateX(0)",
          willChange: "transform, width",
        }}
      >
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: showLabels ? "space-between" : "center",
            padding: showLabels ? "16px 12px 16px 18px" : "16px 0",
            minHeight: 60,
            borderBottom: "1px solid var(--color-border-muted)",
            flexShrink: 0,
          }}
        >
          {/* Logo wordmark */}
          {showLabels && (
            <div style={{ display: "flex", alignItems: "center", gap: 9, overflow: "hidden" }}>
              <div
                style={{
                  width: 28, height: 28, borderRadius: 8,
                  background: "var(--gradient-brand)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexShrink: 0,
                  boxShadow: "var(--shadow-glow)",
                }}
              >
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
                  <path d="M3 4L10 2L17 4V10C17 14.4 13.4 17.4 10 18C6.6 17.4 3 14.4 3 10V4Z"
                    stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
                  <path d="M7 10L9 12L13 8"
                    stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <span style={{
                fontWeight: 700, fontSize: 14,
                color: "var(--color-text-primary)",
                whiteSpace: "nowrap", overflow: "hidden",
              }}>
                ForgeAI
              </span>
            </div>
          )}

          {/* Desktop: chevron toggle */}
          {!isMobile && (
            <button
              id="sidebar-toggle-btn"
              onClick={() => setExpanded((p) => !p)}
              aria-label={expanded ? "Collapse sidebar" : "Expand sidebar"}
              title="Toggle sidebar (Ctrl+B)"
              style={{
                width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: "var(--color-surface-overlay)",
                border: "1px solid var(--color-border-default)",
                cursor: "pointer",
                color: "var(--color-text-muted)",
                transition: `background 150ms ease, color 150ms ease`,
              }}
            >
              {expanded ? <ChevronLeft size={14}/> : <ChevronRight size={14}/>}
            </button>
          )}

          {/* Mobile: close button */}
          {isMobile && (
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close sidebar"
              style={{
                width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: "transparent", border: "none",
                cursor: "pointer", color: "var(--color-text-muted)",
              }}
            >
              <X size={15}/>
            </button>
          )}
        </div>

        {/* ── Nav items ────────────────────────────────────────────────── */}
        <nav
          style={{
            flex: 1, padding: "10px 8px",
            display: "flex", flexDirection: "column", gap: 2,
            overflowY: "auto", overflowX: "hidden",
          }}
        >
          {navItems.map(({ href, icon: Icon, label, soon }) => {
            const isActive = !soon && pathname === href;

            /* Soon items — non-interactive span */
            if (soon) {
              return (
                <span
                  key={label}
                  aria-disabled="true"
                  title={!showLabels ? `${label} — coming soon` : undefined}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: showLabels ? "flex-start" : "center",
                    gap: 12,
                    padding: showLabels ? "8px 12px" : "9px 0",
                    borderRadius: 8,
                    fontSize: 13, fontWeight: 500,
                    cursor: "not-allowed",
                    color: "var(--color-text-disabled)",
                    userSelect: "none",
                    whiteSpace: "nowrap",
                  }}
                >
                  <Icon size={15} style={{ flexShrink: 0 }} aria-hidden="true"/>
                  {showLabels && (
                    <>
                      <span style={{ flex: 1 }}>{label}</span>
                      <span style={{
                        fontSize: 9, fontWeight: 700,
                        letterSpacing: "0.06em", textTransform: "uppercase",
                        padding: "2px 5px", borderRadius: 4,
                        background: "var(--color-surface-overlay)",
                        border: "1px solid var(--color-border-muted)",
                        color: "var(--color-text-disabled)",
                      }}>Soon</span>
                    </>
                  )}
                </span>
              );
            }

            /* Active / normal links */
            return (
              <Link
                key={label}
                href={href}
                id={`nav-${label.toLowerCase()}`}
                title={!showLabels ? label : undefined}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: showLabels ? "flex-start" : "center",
                  gap: 12,
                  padding: showLabels ? "8px 12px" : "9px 0",
                  borderRadius: 8,
                  fontSize: 13, fontWeight: 500,
                  textDecoration: "none",
                  whiteSpace: "nowrap",
                  transition: `background 150ms ease, color 150ms ease, border-color 150ms ease`,
                  color: isActive ? "var(--color-brand-400)" : "var(--color-text-secondary)",
                  background: isActive ? "hsl(220,80%,52%,0.1)" : "transparent",
                  border: `1px solid ${isActive ? "hsl(220,80%,52%,0.2)" : "transparent"}`,
                }}
              >
                <Icon
                  size={15}
                  style={{ flexShrink: 0, color: isActive ? "var(--color-brand-400)" : undefined }}
                  aria-hidden="true"
                />
                {showLabels && <span>{label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* ── Footer ──────────────────────────────────────────────────── */}
        {showLabels && (
          <div style={{
            padding: "10px 18px",
            borderTop: "1px solid var(--color-border-muted)",
            flexShrink: 0,
          }}>
            <p style={{ fontSize: 11, color: "var(--color-text-disabled)", whiteSpace: "nowrap" }}>
              Phase 2 · Repository Import
            </p>
          </div>
        )}
      </aside>

      {/* ── Mobile hamburger (fixed, visible when drawer is closed) ─────── */}
      {isMobile && !mobileOpen && (
        <button
          id="mobile-menu-btn"
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          style={{
            position: "fixed", top: 14, left: 14, zIndex: 50,
            width: 36, height: 36, borderRadius: 8,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "var(--color-surface-raised)",
            border: "1px solid var(--color-border-default)",
            cursor: "pointer",
            color: "var(--color-text-primary)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          <Menu size={16}/>
        </button>
      )}

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <main
        style={{
          flex: 1,
          minHeight: "100vh",
          overflowY: "auto",
          marginLeft: isMobile ? 0 : sidebarPx,
          paddingTop: isMobile ? 0 : 0,
          transition: `margin-left ${TRANSITION}`,
        }}
      >
        {children}
      </main>
    </div>
  );
}
