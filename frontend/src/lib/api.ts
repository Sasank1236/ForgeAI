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
