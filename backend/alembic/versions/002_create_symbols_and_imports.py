"""Create symbols and imports tables.

Revision ID: 002
Revises: 001
Create Date: 2026-07-25

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# ── Revision identifiers ──────────────────────────────────────────────────────
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── symbol_type enum ──────────────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE symbol_type AS ENUM ("
        "'function','class','method','constructor','interface','enum',"
        "'struct','variable','constant','type_alias','module','namespace'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$"
    )

    # ── symbol_visibility enum ────────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE symbol_visibility AS ENUM ("
        "'public','private','protected','internal'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$"
    )

    # ── import_type enum ──────────────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE import_type AS ENUM ("
        "'import','from_import','require','dynamic_import',"
        "'include','package','export','re_export','side_effect'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$"
    )

    # ── symbols table ─────────────────────────────────────────────────────────
    op.create_table(
        "symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        # symbol_type — stored as Text then cast to enum
        sa.Column("symbol_type", sa.Text, nullable=False),
        sa.Column("language", sa.String(100), nullable=False),
        sa.Column(
            "parent_symbol_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        # Position
        sa.Column("start_line", sa.Integer, nullable=False),
        sa.Column("end_line", sa.Integer, nullable=False),
        sa.Column("start_column", sa.Integer, nullable=False, server_default="0"),
        sa.Column("end_column", sa.Integer, nullable=False, server_default="0"),
        # Metadata
        sa.Column("visibility", sa.Text, nullable=True),
        sa.Column("signature", sa.Text, nullable=True),
        sa.Column("docstring", sa.Text, nullable=True),
    )

    # Cast symbol_type column to the enum type
    op.execute(
        "ALTER TABLE symbols "
        "ALTER COLUMN symbol_type TYPE symbol_type "
        "USING symbol_type::symbol_type"
    )

    # Cast visibility column to the enum type
    op.execute(
        "ALTER TABLE symbols "
        "ALTER COLUMN visibility TYPE symbol_visibility "
        "USING visibility::symbol_visibility"
    )

    # ── Additional indexes on symbols ─────────────────────────────────────────
    op.create_index(
        "ix_symbols_name",
        "symbols",
        ["name"],
    )
    op.create_index(
        "ix_symbols_symbol_type",
        "symbols",
        ["symbol_type"],
    )
    op.create_index(
        "ix_symbols_language",
        "symbols",
        ["language"],
    )

    # ── imports table ─────────────────────────────────────────────────────────
    op.create_table(
        "imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_symbol", sa.String(500), nullable=True),
        sa.Column("target_module", sa.Text, nullable=False),
        # import_type — stored as Text then cast to enum
        sa.Column("import_type", sa.Text, nullable=False),
        sa.Column("alias", sa.String(500), nullable=True),
    )

    # Cast import_type column to the enum type
    op.execute(
        "ALTER TABLE imports "
        "ALTER COLUMN import_type TYPE import_type "
        "USING import_type::import_type"
    )

    # ── Additional indexes on imports ─────────────────────────────────────────
    op.create_index(
        "ix_imports_target_module",
        "imports",
        ["target_module"],
    )
    op.create_index(
        "ix_imports_import_type",
        "imports",
        ["import_type"],
    )


def downgrade() -> None:
    # ── Drop imports ──────────────────────────────────────────────────────────
    op.drop_index("ix_imports_import_type", table_name="imports")
    op.drop_index("ix_imports_target_module", table_name="imports")
    op.drop_table("imports")

    # ── Drop symbols ──────────────────────────────────────────────────────────
    op.drop_index("ix_symbols_language", table_name="symbols")
    op.drop_index("ix_symbols_symbol_type", table_name="symbols")
    op.drop_index("ix_symbols_name", table_name="symbols")
    op.drop_table("symbols")

    # ── Drop enum types ───────────────────────────────────────────────────────
    import_type = postgresql.ENUM(name="import_type")
    import_type.drop(op.get_bind(), checkfirst=True)

    symbol_visibility = postgresql.ENUM(name="symbol_visibility")
    symbol_visibility.drop(op.get_bind(), checkfirst=True)

    symbol_type = postgresql.ENUM(name="symbol_type")
    symbol_type.drop(op.get_bind(), checkfirst=True)
