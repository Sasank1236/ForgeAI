import { StatsExplorer } from "./StatsExplorer";

export const metadata = {
  title: "System Stats & Telemetry — ForgeAI",
  description: "Real-time system observability, health checks, and database telemetry.",
};

export default function StatsPage() {
  return <StatsExplorer />;
}
