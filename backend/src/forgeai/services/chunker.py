"""Code chunker service.

Provides AST-aware symbol chunking and token sliding window chunking for
source code files before vector embedding.

Phase 4 — Vector Embeddings & Knowledge Base
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog
import tiktoken

from forgeai.models.embedding import ChunkType
from forgeai.models.symbol import Symbol

logger = structlog.get_logger(__name__)


@dataclass
class CodeChunk:
    """Represents an extracted code chunk ready for embedding generation."""

    repository_id: UUID
    file_id: UUID
    symbol_id: UUID | None
    chunk_index: int
    chunk_text: str
    token_count: int
    chunk_type: ChunkType
    start_line: int
    end_line: int


class CodeChunker:
    """Chunks source code files into semantic blocks for vector embeddings."""

    def __init__(
        self,
        default_chunk_size: int = 512,
        default_overlap: int = 64,
        encoding_name: str = "cl100k_base",
    ) -> None:
        self.default_chunk_size = default_chunk_size
        self.default_overlap = default_overlap
        try:
            self._tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception:
            self._tokenizer = None

    def count_tokens(self, text: str) -> int:
        """Estimate token count for a text snippet."""
        if not text:
            return 0
        if self._tokenizer is not None:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                pass
        # Fallback estimation (~4 characters per token)
        return max(1, len(text) // 4)

    def chunk_file(
        self,
        repo_id: UUID,
        file_id: UUID,
        relative_path: str,
        content: str,
        symbols: list[Symbol] | None = None,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> list[CodeChunk]:
        """Produce a list of CodeChunk objects for a source file.

        Uses AST-aware symbol chunking if symbols are present;
        falls back to token sliding window chunking.
        """
        if not content.strip():
            return []

        target_size = chunk_size or self.default_chunk_size
        target_overlap = overlap or self.default_overlap

        # If symbols are available and file has extracted functions/classes, use AST chunking
        if symbols and len(symbols) > 0:
            ast_chunks = self._chunk_by_symbols(
                repo_id=repo_id,
                file_id=file_id,
                relative_path=relative_path,
                content=content,
                symbols=symbols,
                max_chunk_size=target_size,
            )
            if ast_chunks:
                return ast_chunks

        # Fallback: sliding window chunking
        return self._chunk_sliding_window(
            repo_id=repo_id,
            file_id=file_id,
            relative_path=relative_path,
            content=content,
            chunk_size=target_size,
            overlap=target_overlap,
        )

    def _chunk_by_symbols(
        self,
        repo_id: UUID,
        file_id: UUID,
        relative_path: str,
        content: str,
        symbols: list[Symbol],
        max_chunk_size: int,
    ) -> list[CodeChunk]:
        """Extract symbol-based code chunks."""
        chunks: list[CodeChunk] = []
        lines = content.splitlines()
        total_lines = len(lines)

        # File header chunk (first 25 lines: imports, top docstrings)
        header_end = min(25, total_lines)
        if header_end > 0:
            header_text = "\n".join(lines[:header_end])
            header_formatted = f"// File: {relative_path} (Header)\n{header_text}"
            chunks.append(
                CodeChunk(
                    repository_id=repo_id,
                    file_id=file_id,
                    symbol_id=None,
                    chunk_index=len(chunks),
                    chunk_text=header_formatted,
                    token_count=self.count_tokens(header_formatted),
                    chunk_type=ChunkType.file_header,
                    start_line=1,
                    end_line=header_end,
                )
            )

        # Process each symbol
        for sym in symbols:
            if sym.start_line <= 0 or sym.end_line < sym.start_line:
                continue

            sym_start = min(sym.start_line, total_lines)
            sym_end = min(sym.end_line, total_lines)

            # Extract symbol source lines (1-indexed to 0-indexed slice)
            sym_lines = lines[sym_start - 1 : sym_end]
            if not sym_lines:
                continue

            sym_body = "\n".join(sym_lines)

            # Context-rich header snippet
            header_info = f"// Symbol: {sym.symbol_type.value} {sym.name} in {relative_path}:{sym.start_line}"
            if sym.signature:
                header_info += f"\n// Signature: {sym.signature}"

            formatted_chunk = f"{header_info}\n{sym_body}"
            token_count = self.count_tokens(formatted_chunk)

            # If symbol text fits within max_chunk_size, add as single symbol chunk
            if token_count <= max_chunk_size * 1.5:
                chunks.append(
                    CodeChunk(
                        repository_id=repo_id,
                        file_id=file_id,
                        symbol_id=sym.id,
                        chunk_index=len(chunks),
                        chunk_text=formatted_chunk,
                        token_count=token_count,
                        chunk_type=ChunkType.symbol,
                        start_line=sym_start,
                        end_line=sym_end,
                    )
                )
            else:
                # Sub-chunk large symbols using sliding window
                sub_chunks = self._chunk_sliding_window(
                    repo_id=repo_id,
                    file_id=file_id,
                    relative_path=relative_path,
                    content=sym_body,
                    chunk_size=max_chunk_size,
                    overlap=64,
                    start_line_offset=sym_start,
                    symbol_id=sym.id,
                    chunk_type=ChunkType.symbol,
                    start_index=len(chunks),
                )
                chunks.extend(sub_chunks)

        return chunks

    def _chunk_sliding_window(
        self,
        repo_id: UUID,
        file_id: UUID,
        relative_path: str,
        content: str,
        chunk_size: int,
        overlap: int,
        start_line_offset: int = 1,
        symbol_id: UUID | None = None,
        chunk_type: ChunkType = ChunkType.window,
        start_index: int = 0,
    ) -> list[CodeChunk]:
        """Sliding window chunking by line boundary."""
        chunks: list[CodeChunk] = []
        lines = content.splitlines()
        if not lines:
            return chunks

        step = max(1, chunk_size - overlap)
        line_idx = 0
        current_chunk_idx = start_index

        while line_idx < len(lines):
            # Accumulate lines up to target chunk token limit
            accumulated: list[str] = []
            accum_tokens = 0
            end_line_idx = line_idx

            while end_line_idx < len(lines):
                line = lines[end_line_idx]
                line_tokens = self.count_tokens(line)
                if accum_tokens + line_tokens > chunk_size and len(accumulated) > 0:
                    break
                accumulated.append(line)
                accum_tokens += line_tokens + 1   # +1 for newline
                end_line_idx += 1

            if not accumulated:
                # Handle single line larger than chunk size
                accumulated.append(lines[line_idx])
                end_line_idx = line_idx + 1

            text_body = "\n".join(accumulated)
            header = f"// File: {relative_path} (Lines {start_line_offset + line_idx}-{start_line_offset + end_line_idx - 1})\n"
            full_text = header + text_body

            chunks.append(
                CodeChunk(
                    repository_id=repo_id,
                    file_id=file_id,
                    symbol_id=symbol_id,
                    chunk_index=current_chunk_idx,
                    chunk_text=full_text,
                    token_count=self.count_tokens(full_text),
                    chunk_type=chunk_type,
                    start_line=start_line_offset + line_idx,
                    end_line=start_line_offset + end_line_idx - 1,
                )
            )

            current_chunk_idx += 1
            if end_line_idx >= len(lines):
                break

            # Slide forward by calculated line step
            lines_in_chunk = end_line_idx - line_idx
            lines_to_advance = max(1, lines_in_chunk - max(1, overlap // 15))
            line_idx += lines_to_advance

        return chunks
