"""Add short-lived Arabic scheduling assistant preview drafts."""

import sqlalchemy as sa
from alembic import op

revision = "0009_pm004b_assistant"
down_revision = "0008_pm003c_editor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "assistant_rule_drafts" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "assistant_rule_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("timetable_project_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("source_text", sa.String(2000), nullable=False),
        sa.Column("parser_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("proposals", sa.JSON(), nullable=False),
        sa.Column("clarifications", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_rule_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["timetable_project_id"], ["timetable_projects.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("token_hash"),
    )
    for column in ("tenant_id", "timetable_project_id", "token_hash", "status", "expires_at"):
        op.create_index(f"ix_assistant_rule_drafts_{column}", "assistant_rule_drafts", [column])


def downgrade() -> None:
    op.drop_table("assistant_rule_drafts")
