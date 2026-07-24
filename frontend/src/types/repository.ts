// TypeScript interfaces mirroring the backend Pydantic schemas.

export interface RepositoryStats {
  total_files: number;
  code_files: number;
  total_size_bytes: number;
  languages: Record<string, number>;
}

export type RepositoryStatus = "pending" | "scanning" | "ready" | "error";

export interface Repository {
  id: string;
  name: string;
  root_path: string;
  status: RepositoryStatus;
  scan_version: number;
  default_branch: string | null;
  current_commit: string | null;
  git_remote: string | null;
  created_at: string;
  last_scanned: string | null;
  stats: RepositoryStats | null;
}

export interface RepositoryListItem {
  id: string;
  name: string;
  root_path: string;
  status: RepositoryStatus;
  scan_version: number;
  last_scanned: string | null;
  stats: RepositoryStats | null;
}

export interface ImportResponse {
  repository_id: string;
  status: string;
  files_scanned: number;
  languages: Record<string, number>;
  scan_time_ms: number;
}

export interface FileItem {
  id: string;
  repository_id: string;
  relative_path: string;
  language: string | null;
  extension: string;
  size: number;
  is_binary: boolean;
  mime_type: string | null;
  line_count: number;
  last_modified: string | null;
  parsed: boolean;
  symbols_count: number;
}

export interface FilesListResponse {
  items: FileItem[];
  total: number;
  page: number;
  page_size: number;
}
