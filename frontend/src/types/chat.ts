// TypeScript interfaces for Phase 6 Repository Chat & Grounded QA

export type MessageRole = "user" | "assistant" | "system";

export interface CitationItem {
  file_id: string;
  relative_path: string;
  symbol_id?: string | null;
  name?: string | null;
  start_line: number;
  end_line: number;
  score: number;
}

export interface ChatSessionCreate {
  title?: string;
}

export interface ChatSessionResponse {
  id: string;
  repository_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatSessionListResponse {
  items: ChatSessionResponse[];
  total: number;
}

export interface ChatMessageCreate {
  content: string;
  search_type?: string;
  min_score?: number;
}

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  citations: CitationItem[];
  token_count: number;
  created_at: string;
}
