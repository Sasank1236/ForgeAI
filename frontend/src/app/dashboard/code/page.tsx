import { CodeExplorer } from "./CodeExplorer";

export const metadata = {
  title: "Code Explorer — ForgeAI",
  description: "Browse indexed codebase files and Tree-sitter AST code symbols.",
};

export default function CodePage() {
  return <CodeExplorer />;
}
