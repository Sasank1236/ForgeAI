// TypeScript interfaces for Phase 4 Vector Embeddings & Knowledge Base

export interface IndexRequest {
  force_reindex?: boolean;
  chunk_size?: number;
  overlap?: number;
  languages?: string[];
}

export interface ChunkInfo {
  chunk_index: number;
  chunk_type: string;
  start_line: number;
  end_line: number;
  token_count: number;
}

export interface IndexStatsResponse {
  total_chunks: number;
  total_embedded_files: number;
  total_tokens: number;
  duration_ms: number;
  by_chunk_type: Record<string, number>;
}

export interface IndexResponse {
  repository_id: string;
  status: string;
  stats: IndexStatsResponse;
}

export interface EmbeddingSearchResult {
  id: string;
  repository_id: string;
  file_id: string;
  relative_path: string;
  symbol_id: string | null;
  chunk_index: number;
  chunk_type: string;
  chunk_text: string;
  start_line: number;
  end_line: number;
  token_count: number;
  similarity: number;
}
