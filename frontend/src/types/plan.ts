// TypeScript interfaces for Phase 7 AI Task Planner & Code Suggestions

export type PlanStatus = "draft" | "in_progress" | "completed" | "failed";

export interface PlanCreateRequest {
  goal_description: string;
  title?: string;
}

export interface PlanStepResponse {
  id: string;
  plan_id: string;
  step_index: number;
  title: string;
  description: string;
  target_path: string;
  code_diff?: string | null;
  status: PlanStatus;
  created_at: string;
}

export interface TaskPlanResponse {
  id: string;
  repository_id: string;
  title: string;
  goal_description: string;
  status: PlanStatus;
  impact_summary?: string | null;
  created_at: string;
  updated_at: string;
  steps: PlanStepResponse[];
}

export interface TaskPlanListResponse {
  items: TaskPlanResponse[];
  total: number;
}

export interface CodeSuggestionRequest {
  file_path: string;
  instruction: string;
  context_lines?: number;
}

export interface CodeSuggestionResponse {
  target_path: string;
  original_snippet: string;
  suggested_snippet: string;
  diff: string;
  explanation: string;
}
