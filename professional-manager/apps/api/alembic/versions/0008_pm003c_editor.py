"""Add PM-003C working timetable editor, history, locks and snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0008_pm003c_editor"
down_revision = "0007_pm003b_solve_runs"
branch_labels = None
depends_on = None

TABLES = (
    "working_timetables",
    "working_timetable_entries",
    "working_timetable_entry_teachers",
    "working_timetable_entry_sections",
    "working_timetable_entry_resources",
    "timetable_edit_locks",
    "timetable_edit_changes",
    "timetable_audit_events",
    "timetable_snapshots",
    "timetable_repair_previews",
)


def upgrade() -> None:
    if set(TABLES).issubset(set(sa.inspect(op.get_bind()).get_table_names())):
        return
    op.create_table(
        "working_timetables",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("timetable_project_id", sa.Uuid(), nullable=False),
        sa.Column("source_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("parent_timetable_id", sa.Uuid()),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("history_cursor", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_by", sa.String(200)),
        sa.Column("change_summary", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timetable_project_id"], ["timetable_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_candidate_id"], ["timetable_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_timetable_id"], ["working_timetables.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "timetable_project_id", "version_number"),
        sa.CheckConstraint("revision > 0"),
        sa.CheckConstraint("history_cursor >= 0"),
    )
    for column in ("tenant_id", "timetable_project_id", "source_candidate_id", "parent_timetable_id"):
        op.create_index(f"ix_working_timetables_{column}", "working_timetables", [column])
    op.create_index(
        "uq_current_working_timetable_per_project",
        "working_timetables",
        ["tenant_id", "timetable_project_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
        sqlite_where=sa.text("is_current = 1"),
    )
    op.create_table(
        "working_timetable_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("working_timetable_id", sa.Uuid(), nullable=False),
        sa.Column("source_entry_id", sa.Uuid()),
        sa.Column("occurrence_id", sa.String(220), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("slot_id", sa.String(220), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("project_cycle_week_index", sa.Integer(), nullable=False),
        sa.Column("weekday_index", sa.Integer(), nullable=False),
        sa.Column("starts_at_minute", sa.Integer(), nullable=False),
        sa.Column("ends_at_minute", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["working_timetable_id"], ["working_timetables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entry_id"], ["timetable_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignment_id"], ["teaching_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "working_timetable_id", "occurrence_id"),
        sa.CheckConstraint("project_cycle_week_index >= 0"),
        sa.CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        sa.CheckConstraint("starts_at_minute < ends_at_minute"),
    )
    for column in ("tenant_id", "working_timetable_id", "source_entry_id", "assignment_id", "subject_id", "school_id"):
        op.create_index(f"ix_working_timetable_entries_{column}", "working_timetable_entries", [column])
    for table, entry_column, target, target_table in (
        ("working_timetable_entry_teachers", "working_timetable_entry_id", "teacher_id", "teachers"),
        ("working_timetable_entry_sections", "working_timetable_entry_id", "section_id", "sections"),
        ("working_timetable_entry_resources", "working_timetable_entry_id", "resource_id", "resources"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column(entry_column, sa.Uuid(), nullable=False),
            sa.Column(target, sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint([entry_column], ["working_timetable_entries.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint([target], [f"{target_table}.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("tenant_id", entry_column, target),
        )
        for column in ("tenant_id", entry_column, target):
            op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_table(
        "timetable_edit_locks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("working_timetable_id", sa.Uuid(), nullable=False),
        sa.Column("lock_type", sa.String(30), nullable=False),
        sa.Column("occurrence_id", sa.String(220)),
        sa.Column("teacher_id", sa.Uuid()), sa.Column("section_id", sa.Uuid()),
        sa.Column("school_id", sa.Uuid()), sa.Column("project_cycle_week_index", sa.Integer()),
        sa.Column("weekday_index", sa.Integer()), sa.Column("starts_at_minute", sa.Integer()),
        sa.Column("ends_at_minute", sa.Integer()), sa.Column("label", sa.String(200), nullable=False),
        sa.Column("created_by", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["working_timetable_id"], ["working_timetables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("lock_type IN ('occurrence','teacher','section','day','time_range','week','region')"),
        sa.CheckConstraint("weekday_index IS NULL OR (weekday_index >= 0 AND weekday_index <= 6)"),
        sa.CheckConstraint("project_cycle_week_index IS NULL OR project_cycle_week_index >= 0"),
        sa.CheckConstraint("starts_at_minute IS NULL OR ends_at_minute IS NULL OR starts_at_minute < ends_at_minute"),
    )
    for column in ("tenant_id", "working_timetable_id", "lock_type"):
        op.create_index(f"ix_timetable_edit_locks_{column}", "timetable_edit_locks", [column])
    op.create_table(
        "timetable_edit_changes",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("working_timetable_id", sa.Uuid(), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(30), nullable=False), sa.Column("before_data", sa.JSON(), nullable=False),
        sa.Column("after_data", sa.JSON(), nullable=False), sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["working_timetable_id"], ["working_timetables.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "working_timetable_id", "sequence"),
    )
    op.create_index("ix_timetable_edit_changes_tenant_id", "timetable_edit_changes", ["tenant_id"])
    op.create_index("ix_timetable_edit_changes_working_timetable_id", "timetable_edit_changes", ["working_timetable_id"])
    op.create_table(
        "timetable_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("working_timetable_id", sa.Uuid(), nullable=False), sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(30), nullable=False), sa.Column("before_data", sa.JSON(), nullable=False),
        sa.Column("after_data", sa.JSON(), nullable=False), sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("actor_reference", sa.String(200)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["working_timetable_id"], ["working_timetables.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_timetable_audit_events_tenant_id", "timetable_audit_events", ["tenant_id"])
    op.create_index("ix_timetable_audit_events_working_timetable_id", "timetable_audit_events", ["working_timetable_id"])
    for table, extra_columns in (
        ("timetable_snapshots", [sa.Column("name", sa.String(200), nullable=False), sa.Column("source_revision", sa.Integer(), nullable=False), sa.Column("entries_snapshot", sa.JSON(), nullable=False), sa.Column("created_by", sa.String(200))]),
        ("timetable_repair_previews", [sa.Column("revision", sa.Integer(), nullable=False), sa.Column("occurrence_id", sa.String(220), nullable=False), sa.Column("target_slot_id", sa.String(220), nullable=False), sa.Column("changes", sa.JSON(), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False), sa.Column("total_moved_occurrences", sa.Integer(), nullable=False), sa.Column("penalty_before", sa.Integer(), nullable=False), sa.Column("penalty_after", sa.Integer(), nullable=False), sa.Column("applied_at", sa.DateTime(timezone=True))]),
    ):
        op.create_table(
            table, sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("working_timetable_id", sa.Uuid(), nullable=False), *extra_columns,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["working_timetable_id"], ["working_timetables.id"], ondelete="CASCADE"),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.create_index(f"ix_{table}_working_timetable_id", table, ["working_timetable_id"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
