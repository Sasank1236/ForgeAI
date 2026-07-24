// Server Component — exports metadata, delegates all layout interactivity to DashboardShell
import type { Metadata } from "next";
import DashboardShell from "./NavSidebar";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "ForgeAI repository dashboard — manage imported codebases.",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DashboardShell>{children}</DashboardShell>;
}
