// TypeScript interfaces for Phase 8 Auto Documentation Generation

export type DocType = "readme" | "architecture" | "api_reference" | "symbol_doc";
export type DocStatus = "draft" | "generated" | "updated";

export interface DocGenerateRequest {
  doc_type: DocType;
  title?: string;
  custom_instructions?: string;
}

export interface DocUpdateRequest {
  content: string;
  title?: string;
}

export interface DocumentationResponse {
  id: string;
  repository_id: string;
  doc_type: DocType;
  title: string;
  content: string;
  file_path?: string | null;
  status: DocStatus;
  created_at: string;
  updated_at: string;
}

export interface DocumentationListResponse {
  items: DocumentationResponse[];
  total: number;
}
