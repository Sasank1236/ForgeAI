// TypeScript interfaces for Phase 5 Repository Search (Semantic + Hybrid)

export type SearchType = "hybrid" | "semantic" | "keyword" | "symbol";

export interface SearchQueryRequest {
  query: string;
  search_type?: SearchType;
  limit?: number;
  min_score?: number;
  language?: string;
  extension?: string;
}

export interface SearchResultItem {
  id: string;
  file_id: string;
  relative_path: string;
  symbol_id?: string | null;
  name?: string | null;
  chunk_text: string;
  chunk_type: string;
  start_line: number;
  end_line: number;
  score: number;
  match_type: "hybrid" | "semantic" | "keyword" | "symbol";
}

export interface SearchResponse {
  query: string;
  search_type: SearchType;
  total_hits: number;
  duration_ms: number;
  results: SearchResultItem[];
}
