"""Add persisted CP-SAT solve runs, candidates and relational entries."""

import sqlalchemy as sa
from alembic import op

revision = "0007_pm003b_solve_runs"
down_revision = "0006_pm003a_projects_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    expected_tables = {
        "timetable_solve_runs",
        "timetable_candidates",
        "timetable_entries",
        "timetable_entry_teachers",
        "timetable_entry_sections",
        "timetable_entry_resources",
    }
    if expected_tables.issubset(set(sa.inspect(op.get_bind()).get_table_names())):
        # Migration 0001 intentionally evaluates the current foundation metadata on a
        # clean database. Existing installations reach 0007 without these tables.
        return
    op.create_table(
        "timetable_solve_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("timetable_project_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("requested_candidates", sa.Integer(), nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("solver_status", sa.String(30)),
        sa.Column("solver_name", sa.String(100)),
        sa.Column("solver_version", sa.String(50)),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["timetable_project_id"], ["timetable_projects.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint("requested_candidates >= 1 AND requested_candidates <= 5"),
        sa.CheckConstraint("time_limit_seconds >= 1 AND time_limit_seconds <= 60"),
    )
    op.create_index("ix_timetable_solve_runs_tenant_id", "timetable_solve_runs", ["tenant_id"])
    op.create_index(
        "ix_timetable_solve_runs_timetable_project_id",
        "timetable_solve_runs",
        ["timetable_project_id"],
    )
    op.create_index("ix_timetable_solve_runs_status", "timetable_solve_runs", ["status"])
    op.create_index(
        "ix_timetable_solve_runs_input_fingerprint",
        "timetable_solve_runs",
        ["input_fingerprint"],
    )
    op.create_index(
        "uq_active_solve_run_per_project",
        "timetable_solve_runs",
        ["tenant_id", "timetable_project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued','running')"),
        sqlite_where=sa.text("status IN ('queued','running')"),
    )
    op.create_table(
        "timetable_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("solve_run_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("solver_status", sa.String(30), nullable=False),
        sa.Column("total_penalty", sa.Integer(), nullable=False),
        sa.Column("penalty_breakdown", sa.JSON(), nullable=False),
        sa.Column("solve_time_ms", sa.Integer(), nullable=False),
        sa.Column("diversity_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["solve_run_id"], ["timetable_solve_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "solve_run_id", "rank"),
    )
    op.create_index("ix_timetable_candidates_tenant_id", "timetable_candidates", ["tenant_id"])
    op.create_index("ix_timetable_candidates_solve_run_id", "timetable_candidates", ["solve_run_id"])
    op.create_table(
        "timetable_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["candidate_id"], ["timetable_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["teaching_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "candidate_id", "occurrence_id"),
        sa.CheckConstraint("project_cycle_week_index >= 0"),
        sa.CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        sa.CheckConstraint("starts_at_minute < ends_at_minute"),
    )
    for column in ("tenant_id", "candidate_id", "assignment_id", "subject_id", "school_id"):
        op.create_index(f"ix_timetable_entries_{column}", "timetable_entries", [column])
    for table, target, target_table in (
        ("timetable_entry_teachers", "teacher_id", "teachers"),
        ("timetable_entry_sections", "section_id", "sections"),
        ("timetable_entry_resources", "resource_id", "resources"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("timetable_entry_id", sa.Uuid(), nullable=False),
            sa.Column(target, sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["timetable_entry_id"], ["timetable_entries.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint([target], [f"{target_table}.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("tenant_id", "timetable_entry_id", target),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.create_index(f"ix_{table}_timetable_entry_id", table, ["timetable_entry_id"])
        op.create_index(f"ix_{table}_{target}", table, [target])


def downgrade() -> None:
    for table in ("timetable_entry_resources", "timetable_entry_sections", "timetable_entry_teachers"):
        op.drop_table(table)
    op.drop_table("timetable_entries")
    op.drop_table("timetable_candidates")
    op.drop_table("timetable_solve_runs")
