"""Create repositories and repository_files tables.

Revision ID: 001
Revises:
Create Date: 2026-07-24

Phase 2 — Repository Import & File Scanner
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# ── Revision identifiers ──────────────────────────────────────────────────────
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── repository_status enum ────────────────────────────────────────────────
    # Use raw DDL so this is idempotent (safe to re-run if enum already exists)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE repository_status AS ENUM ('pending','scanning','ready','error'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$"
    )

    # ── repositories table ────────────────────────────────────────────────────
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("root_path", sa.Text, nullable=False, unique=True),
        # Use Text column referencing the pre-created enum type via raw SQL type
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("scan_version", sa.Integer, nullable=False, server_default="1"),
        # Git info
        sa.Column("default_branch", sa.String(255), nullable=True),
        sa.Column("current_commit", sa.String(40), nullable=True),
        sa.Column("git_remote", sa.Text, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_scanned", sa.DateTime(timezone=True), nullable=True),
    )
    # Cast the column to use the enum type.
    # Must drop server_default first; PostgreSQL cannot auto-cast a text default.
    op.execute("ALTER TABLE repositories ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE repositories "
        "ALTER COLUMN status TYPE repository_status "
        "USING status::repository_status"
    )
    op.execute(
        "ALTER TABLE repositories "
        "ALTER COLUMN status SET DEFAULT 'pending'::repository_status"
    )

    # ── repository_files table ────────────────────────────────────────────────
    op.create_table(
        "repository_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Paths
        sa.Column("relative_path", sa.Text, nullable=False),
        sa.Column("absolute_path", sa.Text, nullable=False),
        # Language & type
        sa.Column("language", sa.String(100), nullable=True),
        sa.Column("extension", sa.String(50), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("is_binary", sa.Boolean, nullable=False, server_default="false"),
        # Content metrics
        sa.Column("size", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("line_count", sa.Integer, nullable=False, server_default="0"),
        # Phase 3 placeholders
        sa.Column("parsed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("symbols_count", sa.Integer, nullable=False, server_default="0"),
        # Unique constraint: one path per repository
        sa.UniqueConstraint("repository_id", "relative_path", name="uq_repo_file_path"),
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    op.create_index(
        "ix_repository_files_language",
        "repository_files",
        ["language"],
    )
    op.create_index(
        "ix_repository_files_extension",
        "repository_files",
        ["extension"],
    )


def downgrade() -> None:
    op.drop_index("ix_repository_files_extension", table_name="repository_files")
    op.drop_index("ix_repository_files_language", table_name="repository_files")
    op.drop_table("repository_files")
    op.drop_table("repositories")

    # Drop the enum type
    repository_status = postgresql.ENUM(name="repository_status")
    repository_status.drop(op.get_bind(), checkfirst=True)
