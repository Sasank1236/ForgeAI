"use client";

import { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  Send,
  Plus,
  Trash2,
  Loader2,
  FileCode2,
  Sparkles,
  Bot,
  User,
  Copy,
  Check,
} from "lucide-react";
import {
  createChatSession,
  deleteChatSession,
  getChatSession,
  listChatSessions,
  listRepositories,
} from "@/lib/api";
import type { RepositoryListItem } from "@/types/repository";
import type {
  ChatMessageResponse,
  ChatSessionResponse,
  CitationItem,
} from "@/types/chat";

export function ChatInterface() {
  const [repos, setRepos] = useState<RepositoryListItem[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageResponse[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<CitationItem[]>([]);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Fetch repositories
  useEffect(() => {
    let isMounted = true;
    listRepositories()
      .then((data) => {
        if (isMounted) {
          setRepos(data);
          if (data.length > 0) {
            setSelectedRepoId(data[0].id);
          }
        }
      })
      .finally(() => {
        if (isMounted) setLoadingRepos(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch sessions when selected repository changes
  useEffect(() => {
    if (!selectedRepoId) return;
    let isMounted = true;
    listChatSessions(selectedRepoId)
      .then((res) => {
        if (isMounted) {
          setSessions(res.items);
          if (res.items.length > 0) {
            setActiveSessionId(res.items[0].id);
          } else {
            setActiveSessionId(null);
            setMessages([]);
          }
        }
      })
      .catch(() => {
        if (isMounted) setSessions([]);
      })
      .finally(() => {
        if (isMounted) setLoadingSessions(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedRepoId]);

  // Fetch messages when active session changes
  useEffect(() => {
    let isMounted = true;
    if (!activeSessionId) {
      return;
    }
    getChatSession(activeSessionId)
      .then((res) => {
        if (isMounted) {
          setMessages(res.messages);
        }
      })
      .catch(() => {
        if (isMounted) setMessages([]);
      })
      .finally(() => {
        if (isMounted) setLoadingMessages(false);
      });
    return () => {
      isMounted = false;
    };
  }, [activeSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  // Create new session
  const handleCreateSession = async () => {
    if (!selectedRepoId) return;
    try {
      const sess = await createChatSession(selectedRepoId, {
        title: "New Conversation",
      });
      setSessions((prev) => [sess, ...prev]);
      setActiveSessionId(sess.id);
      setMessages([]);
    } catch {
      alert("Failed to create chat session.");
    }
  };

  // Delete session
  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;
    try {
      await deleteChatSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch {
      alert("Failed to delete session.");
    }
  };

  // Send message via SSE Streaming
  const handleSendMessage = async () => {
    if (!inputPrompt.trim() || sending) return;
    let targetSessionId = activeSessionId;

    // Auto-create session if none active
    if (!targetSessionId) {
      if (!selectedRepoId) return;
      try {
        const newSess = await createChatSession(selectedRepoId, {
          title: inputPrompt.trim().slice(0, 30),
        });
        setSessions((prev) => [newSess, ...prev]);
        setActiveSessionId(newSess.id);
        targetSessionId = newSess.id;
      } catch {
        alert("Failed to create conversation session.");
        return;
      }
    }

    const promptText = inputPrompt.trim();
    setInputPrompt("");
    setSending(true);
    setStreamingContent("");
    setStreamingCitations([]);

    // Optimistically add user message
    const userMsg: ChatMessageResponse = {
      id: "temp-" + Date.now(),
      session_id: targetSessionId,
      role: "user",
      content: promptText,
      citations: [],
      token_count: 0,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

    try {
      const response = await fetch(`${apiBase}/chat/sessions/${targetSessionId}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: promptText, search_type: "hybrid" }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Streaming request failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let accumulatedText = "";
      let accumulatedCitations: CitationItem[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.slice(6));
              if (payload.event === "citations") {
                accumulatedCitations = JSON.parse(payload.data);
                setStreamingCitations(accumulatedCitations);
              } else if (payload.event === "token") {
                accumulatedText += payload.data;
                setStreamingContent(accumulatedText);
              } else if (payload.event === "done") {
                // Save complete assistant message
                const assistantMsg: ChatMessageResponse = {
                  id: payload.data || ("msg-" + Date.now()),
                  session_id: targetSessionId,
                  role: "assistant",
                  content: accumulatedText,
                  citations: accumulatedCitations,
                  token_count: accumulatedText.split(" ").length,
                  created_at: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, assistantMsg]);
                setStreamingContent("");
                setStreamingCitations([]);
              }
            } catch {
              // Ignore line parse errors
            }
          }
        }
      }
    } catch {
      // Fallback assistant response
      const fallbackMsg: ChatMessageResponse = {
        id: "err-" + Date.now(),
        session_id: targetSessionId,
        role: "assistant",
        content: "Sorry, an error occurred while streaming the AI response.",
        citations: [],
        token_count: 0,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, fallbackMsg]);
      setStreamingContent("");
      setStreamingCitations([]);
    } finally {
      setSending(false);
    }
  };

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-gray-950 text-gray-100">
      {/* ── Sessions Sidebar ──────────────────────────────────────────────── */}
      <aside className="w-72 border-r border-gray-800 bg-gray-900/60 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Repository
            </span>
            <button
              onClick={handleCreateSession}
              disabled={!selectedRepoId}
              className="btn btn-primary text-xs px-2.5 py-1 flex items-center gap-1"
            >
              <Plus size={13} />
              New Chat
            </button>
          </div>

          <select
            className="w-full bg-gray-900 border border-gray-800 rounded-lg text-xs p-2 text-gray-200 focus:outline-none focus:border-blue-500"
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            disabled={loadingRepos}
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingSessions ? (
            <div className="py-8 flex justify-center text-gray-500">
              <Loader2 size={16} className="animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-500">
              No chat history yet. Click &quot;New Chat&quot; to start.
            </div>
          ) : (
            sessions.map((sess) => {
              const isActive = activeSessionId === sess.id;
              return (
                <div
                  key={sess.id}
                  onClick={() => setActiveSessionId(sess.id)}
                  className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                    isActive
                      ? "bg-blue-600/20 text-blue-400 font-medium border border-blue-800/60"
                      : "text-gray-300 hover:bg-gray-800/60 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <MessageSquare size={13} className="shrink-0 text-blue-400" />
                    <span className="truncate">{sess.title}</span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(sess.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-opacity"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* ── Main Chat Area ───────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-gray-950">
        {/* Messages Header */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between bg-gray-900/40">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-200">
            <Bot size={18} className="text-blue-400" />
            <span>ForgeAI Grounded Assistant</span>
          </div>
          <div className="text-xs text-gray-500 flex items-center gap-1 font-mono">
            <Sparkles size={12} className="text-purple-400" />
            GPT-4o-mini Grounded Context
          </div>
        </div>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {loadingMessages ? (
            <div className="py-16 flex flex-col items-center justify-center text-gray-500 gap-2 text-xs">
              <Loader2 size={20} className="animate-spin text-blue-500" />
              <span>Loading conversation messages…</span>
            </div>
          ) : messages.length === 0 && !streamingContent ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 max-w-lg mx-auto">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center"
                style={{ background: "var(--gradient-brand)" }}
              >
                <Sparkles size={24} className="text-white" />
              </div>
              <h3 className="font-bold text-lg text-gray-100">
                Ask anything about your codebase
              </h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                ForgeAI searches your repository AST symbols, vector embeddings, and full-text code chunks to give line-level grounded answers.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full text-left text-xs pt-2">
                {[
                  "Explain how authentication works",
                  "Find all database query functions",
                  "What components use State?",
                  "Show imports for main.py",
                ].map((sample, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInputPrompt(sample);
                    }}
                    className="p-2.5 rounded-xl bg-gray-900/80 border border-gray-800 hover:border-gray-700 text-gray-300 hover:text-white transition-all truncate"
                  >
                    💡 {sample}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => {
                const isUser = msg.role === "user";
                return (
                  <div
                    key={msg.id}
                    className={`flex gap-3 max-w-4xl ${
                      isUser ? "ml-auto flex-row-reverse" : "mr-auto"
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${
                        isUser
                          ? "bg-blue-600 text-white"
                          : "bg-purple-950 text-purple-400 border border-purple-800"
                      }`}
                    >
                      {isUser ? <User size={15} /> : <Bot size={15} />}
                    </div>

                    <div className="space-y-2 max-w-3xl">
                      <div
                        className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                          isUser
                            ? "bg-blue-600 text-white font-medium"
                            : "bg-gray-900/90 text-gray-200 border border-gray-800"
                        }`}
                      >
                        <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>

                        {!isUser && (
                          <div className="pt-2 flex items-center justify-end">
                            <button
                              onClick={() => copyToClipboard(msg.content, idx)}
                              className="text-[11px] text-gray-400 hover:text-gray-200 flex items-center gap-1"
                            >
                              {copiedIdx === idx ? (
                                <Check size={11} className="text-emerald-400" />
                              ) : (
                                <Copy size={11} />
                              )}
                              {copiedIdx === idx ? "Copied" : "Copy"}
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Citations Drawer */}
                      {!isUser && msg.citations && msg.citations.length > 0 && (
                        <div className="p-3 rounded-xl bg-gray-900/40 border border-gray-800 space-y-1.5 text-xs">
                          <span className="text-gray-400 font-semibold text-[11px] flex items-center gap-1.5">
                            <FileCode2 size={12} className="text-blue-400" />
                            Grounded Citations ({msg.citations.length})
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.citations.map((cit, cIdx) => (
                              <span
                                key={cIdx}
                                className="px-2 py-1 rounded-md bg-gray-900 border border-gray-800 text-[11px] font-mono text-blue-300 flex items-center gap-1"
                              >
                                <span>{cit.relative_path}</span>
                                <span className="text-gray-500">
                                  L{cit.start_line}-{cit.end_line}
                                </span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Streaming Content Display */}
              {streamingContent && (
                <div className="flex gap-3 max-w-4xl mr-auto animate-fade-in">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold bg-purple-950 text-purple-400 border border-purple-800">
                    <Bot size={15} />
                  </div>
                  <div className="space-y-2 max-w-3xl">
                    <div className="p-4 rounded-2xl text-xs sm:text-sm leading-relaxed bg-gray-900/90 text-gray-200 border border-gray-800">
                      <pre className="whitespace-pre-wrap font-sans">{streamingContent}</pre>
                      <span className="inline-block w-1.5 h-4 bg-blue-400 animate-pulse ml-1" />
                    </div>

                    {streamingCitations.length > 0 && (
                      <div className="p-3 rounded-xl bg-gray-900/40 border border-gray-800 space-y-1.5 text-xs">
                        <span className="text-gray-400 font-semibold text-[11px] flex items-center gap-1.5">
                          <FileCode2 size={12} className="text-blue-400" />
                          Grounded Citations ({streamingCitations.length})
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {streamingCitations.map((cit, cIdx) => (
                            <span
                              key={cIdx}
                              className="px-2 py-1 rounded-md bg-gray-900 border border-gray-800 text-[11px] font-mono text-blue-300 flex items-center gap-1"
                            >
                              <span>{cit.relative_path}</span>
                              <span className="text-gray-500">
                                L{cit.start_line}-{cit.end_line}
                              </span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-gray-800 bg-gray-900/60">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 max-w-4xl mx-auto"
          >
            <input
              type="text"
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              placeholder="Ask a question about your repository code..."
              disabled={sending}
              className="flex-1 input bg-gray-900 border-gray-800 text-xs sm:text-sm text-gray-100 placeholder-gray-500 rounded-xl py-3 px-4 focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={sending || !inputPrompt.trim()}
              className="btn btn-primary p-3 rounded-xl flex items-center justify-center shrink-0"
            >
              {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
