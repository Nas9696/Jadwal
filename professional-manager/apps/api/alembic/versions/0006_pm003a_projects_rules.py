"""Add PM-003A project phase alignment and scheduling rules."""

import sqlalchemy as sa
from alembic import op

revision = "0006_pm003a_projects_rules"
down_revision = "0005_pm002d_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    project_columns = {item["name"] for item in inspector.get_columns("timetable_projects")}
    if "description" not in project_columns:
        op.add_column("timetable_projects", sa.Column("description", sa.String(500)))
    scope_columns = {item["name"] for item in inspector.get_columns("timetable_project_schools")}
    if "cycle_phase_offset" not in scope_columns:
        op.add_column(
            "timetable_project_schools",
            sa.Column("cycle_phase_offset", sa.Integer(), nullable=False, server_default="0"),
        )
    if "scheduling_rules" not in inspector.get_table_names():
        op.create_table(
            "scheduling_rules",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("timetable_project_id", sa.Uuid(), nullable=False),
            sa.Column("label", sa.String(200), nullable=False),
            sa.Column("description", sa.String(500)),
            sa.Column("rule_type", sa.String(80), nullable=False),
            sa.Column("severity", sa.String(10), nullable=False),
            sa.Column("weight", sa.Integer()),
            sa.Column("selector", sa.JSON(), nullable=False),
            sa.Column("parameters", sa.JSON(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["timetable_project_id"], ["timetable_projects.id"], ondelete="CASCADE"
            ),
            sa.CheckConstraint("severity IN ('hard','soft')"),
            sa.CheckConstraint("weight IS NULL OR weight > 0"),
        )
        op.create_index("ix_scheduling_rules_tenant_id", "scheduling_rules", ["tenant_id"])
        op.create_index(
            "ix_scheduling_rules_timetable_project_id", "scheduling_rules", ["timetable_project_id"]
        )
        op.create_index("ix_scheduling_rules_rule_type", "scheduling_rules", ["rule_type"])


def downgrade() -> None:
    op.drop_table("scheduling_rules")
    op.drop_column("timetable_project_schools", "cycle_phase_offset")
    op.drop_column("timetable_projects", "description")
