"""Create vector embeddings table and pgvector extension.

Revision ID: 003
Revises: 002
Create Date: 2026-08-12

Phase 4 — Vector Embeddings & Knowledge Base
"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# ── Revision identifiers ──────────────────────────────────────────────────────
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Enable pgvector extension ──────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # ── 2. Create chunk_type enum ─────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE chunk_type AS ENUM ('symbol', 'file_header', 'window'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # ── 3. Create code_embeddings table ───────────────────────────────────────
    op.create_table(
        "code_embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "symbol_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "chunk_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "chunk_type",
            postgresql.ENUM(
                "symbol", "file_header", "window", name="chunk_type", create_type=False
            ),
            nullable=False,
            server_default="window",
        ),
        sa.Column(
            "start_line",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "end_line",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    op.create_index(
        "ix_code_embeddings_repository_id",
        "code_embeddings",
        ["repository_id"],
    )
    op.create_index(
        "ix_code_embeddings_file_id",
        "code_embeddings",
        ["file_id"],
    )
    op.create_index(
        "ix_code_embeddings_symbol_id",
        "code_embeddings",
        ["symbol_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_code_embeddings_symbol_id", table_name="code_embeddings")
    op.drop_index("ix_code_embeddings_file_id", table_name="code_embeddings")
    op.drop_index("ix_code_embeddings_repository_id", table_name="code_embeddings")
    op.drop_table("code_embeddings")
    op.execute("DROP TYPE IF EXISTS chunk_type;")
