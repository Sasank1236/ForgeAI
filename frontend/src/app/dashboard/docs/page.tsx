import { DocExplorer } from "./DocExplorer";

export const metadata = {
  title: "Auto Documentation — ForgeAI",
  description: "Automated technical documentation generation (README, Architecture, API Reference).",
};

export default function DocsPage() {
  return <DocExplorer />;
}
