"""Create task_plans and plan_steps tables.

Revision ID: 005
Revises: 004
Create Date: 2026-08-15

Phase 7 — AI Task Planner & Code Suggestions
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# ── Revision identifiers ──────────────────────────────────────────────────────
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create task_plans and plan_steps tables."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. Create task_plans table
    op.create_table(
        "task_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal_description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("impact_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # 2. Create plan_steps table
    op.create_table(
        "plan_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            sa.ForeignKey("task_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_path", sa.String(length=512), nullable=False),
        sa.Column("code_diff", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    """Drop plan_steps and task_plans tables."""
    op.drop_table("plan_steps")
    op.drop_table("task_plans")
