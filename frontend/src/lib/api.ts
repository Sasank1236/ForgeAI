/**
 * Typed Axios client for the ForgeAI backend API.
 * All functions return fully-typed response data (no `.data` unwrapping needed at call sites).
 */

import axios from "axios";
import type {
  FilesListResponse,
  ImportResponse,
  Repository,
  RepositoryListItem,
} from "@/types/repository";
import type {
  ImportListResponse,
  ImportQueryParams,
  ParseRequest,
  ParseResponse,
  SymbolListResponse,
  SymbolQueryParams,
} from "@/types/parser";
import type {
  IndexRequest,
  IndexResponse,
  IndexStatsResponse,
} from "@/types/embedding";
import type {
  SearchQueryRequest,
  SearchResponse,
} from "@/types/search";
import type {
  ChatMessageCreate,
  ChatMessageResponse,
  ChatSessionCreate,
  ChatSessionListResponse,
  ChatSessionResponse,
} from "@/types/chat";
import type {
  CodeSuggestionRequest,
  CodeSuggestionResponse,
  PlanCreateRequest,
  TaskPlanListResponse,
  TaskPlanResponse,
} from "@/types/plan";
import type {
  DocGenerateRequest,
  DocUpdateRequest,
  DocumentationListResponse,
  DocumentationResponse,
} from "@/types/documentation";
import type { SystemHealthResponse } from "@/types/system";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 120_000, // 2 min — large repos can take a while to scan/index/search
});

// ── Repository endpoints ──────────────────────────────────────────────────────

/** Import and scan a local directory. */
export async function importRepository(path: string): Promise<ImportResponse> {
  const { data } = await api.post<ImportResponse>("/repositories/import", {
    path,
  });
  return data;
}

/** List all imported repositories. */
export async function listRepositories(): Promise<RepositoryListItem[]> {
  const { data } = await api.get<RepositoryListItem[]>("/repositories");
  return data;
}

/** Get a single repository by id (includes live stats). */
export async function getRepository(id: string): Promise<Repository> {
  const { data } = await api.get<Repository>(`/repositories/${id}`);
  return data;
}

/** Paginated file list for a repository. */
export async function listFiles(
  id: string,
  page = 1,
  pageSize = 50
): Promise<FilesListResponse> {
  const { data } = await api.get<FilesListResponse>(
    `/repositories/${id}/files`,
    { params: { page, page_size: pageSize } }
  );
  return data;
}

/** Permanently delete a repository and all its scanned files. */
export async function deleteRepository(id: string): Promise<void> {
  await api.delete(`/repositories/${id}`);
}

// ── Phase 3: Code Parsing & Intelligence Endpoints ──────────────────────────

/** Parse source files in a repository using Tree-sitter. */
export async function parseRepository(
  repoId: string,
  request?: ParseRequest
): Promise<ParseResponse> {
  const { data } = await api.post<ParseResponse>(
    `/repositories/${repoId}/parse`,
    request ?? {}
  );
  return data;
}

/** Paginated list of extracted code symbols. */
export async function listSymbols(
  repoId: string,
  params?: SymbolQueryParams
): Promise<SymbolListResponse> {
  const { data } = await api.get<SymbolListResponse>(
    `/repositories/${repoId}/symbols`,
    { params }
  );
  return data;
}

/** Paginated list of extracted import dependencies. */
export async function listImports(
  repoId: string,
  params?: ImportQueryParams
): Promise<ImportListResponse> {
  const { data } = await api.get<ImportListResponse>(
    `/repositories/${repoId}/imports`,
    { params }
  );
  return data;
}

// ── Phase 4: Vector Embeddings & Knowledge Base Endpoints ───────────────────

/** Index a repository into vector embeddings. */
export async function indexRepository(
  repoId: string,
  request?: IndexRequest
): Promise<IndexResponse> {
  const { data } = await api.post<IndexResponse>(
    `/repositories/${repoId}/index`,
    request ?? {}
  );
  return data;
}

/** Fetch vector index statistics for a repository. */
export async function getIndexStats(
  repoId: string
): Promise<IndexStatsResponse> {
  const { data } = await api.get<IndexStatsResponse>(
    `/repositories/${repoId}/index/stats`
  );
  return data;
}

/** Delete all vector embeddings for a repository. */
export async function clearIndex(repoId: string): Promise<{ deleted: number }> {
  const { data } = await api.delete<{ deleted: number }>(
    `/repositories/${repoId}/index`
  );
  return data;
}

// ── Phase 5: Multi-Modal Search Endpoints ────────────────────────────────────

/** Perform semantic, keyword, symbol, or RRF hybrid search over code. */
export async function searchRepository(
  repoId: string,
  request: SearchQueryRequest
): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>(
    `/repositories/${repoId}/search`,
    request
  );
  return data;
}

// ── Phase 6: Repository Chat Endpoints ────────────────────────────────────────

/** Create a new codebase chat session. */
export async function createChatSession(
  repoId: string,
  request?: ChatSessionCreate
): Promise<ChatSessionResponse> {
  const { data } = await api.post<ChatSessionResponse>(
    `/repositories/${repoId}/chat/sessions`,
    request ?? {}
  );
  return data;
}

/** List all chat sessions for a repository. */
export async function listChatSessions(
  repoId: string
): Promise<ChatSessionListResponse> {
  const { data } = await api.get<ChatSessionListResponse>(
    `/repositories/${repoId}/chat/sessions`
  );
  return data;
}

/** Get session details and full message history. */
export async function getChatSession(
  sessionId: string
): Promise<{ session: ChatSessionResponse; messages: ChatMessageResponse[] }> {
  const { data } = await api.get<{
    session: ChatSessionResponse;
    messages: ChatMessageResponse[];
  }>(`/chat/sessions/${sessionId}`);
  return data;
}

/** Delete a chat session. */
export async function deleteChatSession(sessionId: string): Promise<{ deleted: boolean }> {
  const { data } = await api.delete<{ deleted: boolean }>(
    `/chat/sessions/${sessionId}`
  );
  return data;
}

/** Send user prompt and return assistant response with citations. */
export async function sendChatMessage(
  sessionId: string,
  request: ChatMessageCreate
): Promise<ChatMessageResponse> {
  const { data } = await api.post<ChatMessageResponse>(
    `/chat/sessions/${sessionId}/messages`,
    request
  );
  return data;
}

// ── Phase 7: AI Task Planner Endpoints ────────────────────────────────────────

/** Generate an AI task decomposition execution plan. */
export async function createTaskPlan(
  repoId: string,
  request: PlanCreateRequest
): Promise<TaskPlanResponse> {
  const { data } = await api.post<TaskPlanResponse>(
    `/repositories/${repoId}/plans`,
    request
  );
  return data;
}

/** List all execution plans generated for a repository. */
export async function listTaskPlans(
  repoId: string
): Promise<TaskPlanListResponse> {
  const { data } = await api.get<TaskPlanListResponse>(
    `/repositories/${repoId}/plans`
  );
  return data;
}

/** Get plan details and step-by-step diffs. */
export async function getTaskPlan(planId: string): Promise<TaskPlanResponse> {
  const { data } = await api.get<TaskPlanResponse>(`/plans/${planId}`);
  return data;
}

/** Delete a task plan. */
export async function deleteTaskPlan(planId: string): Promise<{ deleted: boolean }> {
  const { data } = await api.delete<{ deleted: boolean }>(`/plans/${planId}`);
  return data;
}

/** Generate targeted code edit suggestion diff for a file. */
export async function generateCodeSuggestion(
  repoId: string,
  request: CodeSuggestionRequest
): Promise<CodeSuggestionResponse> {
  const { data } = await api.post<CodeSuggestionResponse>(
    `/repositories/${repoId}/suggest-code`,
    request
  );
  return data;
}

// ── Phase 8: Auto Documentation Endpoints ─────────────────────────────────────

/** Generate repository technical documentation (README, Architecture, API Reference). */
export async function generateDocumentation(
  repoId: string,
  request: DocGenerateRequest
): Promise<DocumentationResponse> {
  const { data } = await api.post<DocumentationResponse>(
    `/repositories/${repoId}/docs/generate`,
    request
  );
  return data;
}

/** List all generated documentation records for a repository. */
export async function listDocumentation(
  repoId: string
): Promise<DocumentationListResponse> {
  const { data } = await api.get<DocumentationListResponse>(
    `/repositories/${repoId}/docs`
  );
  return data;
}

/** Fetch a single documentation record by UUID. */
export async function getDocumentation(docId: string): Promise<DocumentationResponse> {
  const { data } = await api.get<DocumentationResponse>(`/docs/${docId}`);
  return data;
}

/** Update documentation Markdown content or title. */
export async function updateDocumentation(
  docId: string,
  request: DocUpdateRequest
): Promise<DocumentationResponse> {
  const { data } = await api.put<DocumentationResponse>(`/docs/${docId}`, request);
  return data;
}

/** Delete a documentation record. */
export async function deleteDocumentation(docId: string): Promise<{ deleted: boolean }> {
  const { data } = await api.delete<{ deleted: boolean }>(`/docs/${docId}`);
  return data;
}

// ── Phase 9: System Telemetry & Readiness Endpoints ───────────────────────────

/** Fetch comprehensive system observability and database telemetry metrics. */
export async function getSystemHealth(): Promise<SystemHealthResponse> {
  const { data } = await api.get<SystemHealthResponse>("/health/system");
  return data;
}
