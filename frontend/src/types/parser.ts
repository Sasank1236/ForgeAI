// TypeScript interfaces for Phase 3 Code Parsing & Code Intelligence

export interface SymbolResponse {
  id: string;
  repository_id: string;
  file_id: string;
  name: string;
  symbol_type: string;
  language: string;
  parent_symbol_id: string | null;
  start_line: number;
  end_line: number;
  start_column: number;
  end_column: number;
  visibility: string | null;
  signature: string | null;
  docstring: string | null;
}

export interface SymbolListResponse {
  items: SymbolResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface SymbolQueryParams {
  file_id?: string;
  symbol_type?: string;
  name_query?: string;
  page?: number;
  page_size?: number;
}

export interface ImportRecordResponse {
  id: string;
  repository_id: string;
  file_id: string;
  source_symbol: string | null;
  target_module: string;
  import_type: string;
  alias: string | null;
}

export interface ImportListResponse {
  items: ImportRecordResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ImportQueryParams {
  file_id?: string;
  import_type?: string;
  module_query?: string;
  page?: number;
  page_size?: number;
}

export interface ParseRequest {
  force_reparse?: boolean;
  languages?: string[];
}

export interface LanguageParseStats {
  files_parsed: number;
  symbols_extracted: number;
  imports_extracted: number;
  errors: number;
}

export interface ParseStatsResponse {
  total_files_parsed: number;
  total_symbols_extracted: number;
  total_imports_extracted: number;
  total_failed_files: number;
  duration_ms: number;
  by_language: Record<string, LanguageParseStats>;
}

export interface ParseResponse {
  repository_id: string;
  status: string;
  stats: ParseStatsResponse;
}
