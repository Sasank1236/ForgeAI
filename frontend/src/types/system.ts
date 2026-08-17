// TypeScript interfaces for Phase 9 System Observability & Telemetry

export interface SystemMetrics {
  pid: number;
  uptime_timestamp: number;
  disk_free_gb: number;
  disk_total_gb: number;
  disk_used_percent: number;
}

export interface TelemetryCounts {
  repositories: number;
  files: number;
  symbols: number;
  embeddings: number;
  chat_sessions: number;
  task_plans: number;
  documentation_files: number;
}

export interface SystemHealthResponse {
  status: "ok" | "degraded";
  environment: string;
  debug: boolean;
  python_version: string;
  database: string;
  redis: string;
  system: SystemMetrics;
  telemetry: TelemetryCounts;
}
