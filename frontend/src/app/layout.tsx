import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// ─── Fonts ────────────────────────────────────────────────────────────────────
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

// ─── Metadata ─────────────────────────────────────────────────────────────────
export const metadata: Metadata = {
  title: {
    default: "ForgeAI — Repository-Aware AI Coding Assistant",
    template: "%s | ForgeAI",
  },
  description:
    "ForgeAI understands your entire codebase before helping you write code. " +
    "Semantic search, intelligent chat, task planning, and AI code suggestions — " +
    "all grounded in your actual repository.",
  keywords: [
    "AI coding assistant",
    "repository analysis",
    "code search",
    "software engineering",
    "developer tools",
  ],
  authors: [{ name: "ForgeAI" }],
  robots: "index, follow",
};

export const viewport: Viewport = {
  themeColor: "#0a0e1a",
  width: "device-width",
  initialScale: 1,
};

// ─── Root Layout ──────────────────────────────────────────────────────────────
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full`}
      suppressHydrationWarning
    >
      <body className="h-full antialiased glow-ambient">
        {children}
      </body>
    </html>
  );
}
