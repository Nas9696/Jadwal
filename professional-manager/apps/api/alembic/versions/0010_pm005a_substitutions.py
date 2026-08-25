"""Add waiting policy, absence, need, and substitution assignment tables."""

import sqlalchemy as sa
from alembic import op

revision = "0010_pm005a_substitutions"
down_revision = "0009_pm004b_assistant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "waiting_policies" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "waiting_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("timetable_project_id", sa.Uuid(), nullable=False),
        sa.Column("combined_workload_limit", sa.Integer()),
        sa.Column("daily_waiting_limit", sa.Integer()),
        sa.Column("weekly_waiting_limit", sa.Integer()),
        sa.Column("fairness_weight", sa.Integer(), nullable=False),
        sa.Column("specialty_preference_enabled", sa.Boolean(), nullable=False),
        sa.Column("specialty_preference_weight", sa.Integer(), nullable=False),
        sa.Column("same_school_preference_weight", sa.Integer(), nullable=False),
        sa.Column("exclude_exempt_teachers", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["timetable_project_id"], ["timetable_projects.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("tenant_id", "timetable_project_id"),
        sa.CheckConstraint("combined_workload_limit IS NULL OR combined_workload_limit >= 0"),
        sa.CheckConstraint("daily_waiting_limit IS NULL OR daily_waiting_limit >= 0"),
        sa.CheckConstraint("weekly_waiting_limit IS NULL OR weekly_waiting_limit >= 0"),
        sa.CheckConstraint("fairness_weight >= 0"),
        sa.CheckConstraint("specialty_preference_weight >= 0"),
        sa.CheckConstraint("same_school_preference_weight >= 0"),
    )
    op.create_table(
        "teacher_waiting_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("timetable_project_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column("exempt", sa.Boolean(), nullable=False),
        sa.Column("custom_combined_limit", sa.Integer()),
        sa.Column("custom_daily_limit", sa.Integer()),
        sa.Column("custom_weekly_limit", sa.Integer()),
        sa.Column("notes", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["timetable_project_id"], ["timetable_projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "timetable_project_id", "teacher_id"),
        sa.CheckConstraint("custom_combined_limit IS NULL OR custom_combined_limit >= 0"),
        sa.CheckConstraint("custom_daily_limit IS NULL OR custom_daily_limit >= 0"),
        sa.CheckConstraint("custom_weekly_limit IS NULL OR custom_weekly_limit >= 0"),
    )
    op.create_table(
        "teacher_absences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("timetable_project_id", sa.Uuid(), nullable=False),
        sa.Column("working_timetable_id", sa.Uuid(), nullable=False),
        sa.Column("working_timetable_revision", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column("absence_date", sa.Date(), nullable=False),
        sa.Column("project_cycle_week_index", sa.Integer(), nullable=False),
        sa.Column("weekday_index", sa.Integer(), nullable=False),
        sa.Column("full_day", sa.Boolean(), nullable=False),
        sa.Column("starts_at_minute", sa.Integer()),
        sa.Column("ends_at_minute", sa.Integer()),
        sa.Column("reason_code", sa.String(50)),
        sa.Column("reason_text", sa.String(300)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["timetable_project_id"], ["timetable_projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["working_timetable_id"], ["working_timetables.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("working_timetable_revision > 0"),
        sa.CheckConstraint("project_cycle_week_index >= 0"),
        sa.CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        sa.CheckConstraint(
            "(full_day = TRUE AND starts_at_minute IS NULL AND ends_at_minute IS NULL) OR (full_day = FALSE AND starts_at_minute IS NOT NULL AND ends_at_minute IS NOT NULL AND starts_at_minute < ends_at_minute)"
        ),
        sa.CheckConstraint("status IN ('open','covered','partially_covered','cancelled')"),
    )
    op.create_table(
        "substitution_needs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("absence_id", sa.Uuid(), nullable=False),
        sa.Column("working_timetable_entry_id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_id", sa.String(220), nullable=False),
        sa.Column("absent_teacher_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("project_cycle_week_index", sa.Integer(), nullable=False),
        sa.Column("weekday_index", sa.Integer(), nullable=False),
        sa.Column("starts_at_minute", sa.Integer(), nullable=False),
        sa.Column("ends_at_minute", sa.Integer(), nullable=False),
        sa.Column("source_working_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["absence_id"], ["teacher_absences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["working_timetable_entry_id"], ["working_timetable_entries.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["absent_teacher_id"], ["teachers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("project_cycle_week_index >= 0"),
        sa.CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        sa.CheckConstraint("starts_at_minute < ends_at_minute"),
        sa.CheckConstraint("source_working_revision > 0"),
        sa.CheckConstraint("version > 0"),
        sa.CheckConstraint("status IN ('unassigned','assigned','uncovered','cancelled')"),
    )
    op.create_table(
        "substitution_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("need_id", sa.Uuid(), nullable=False),
        sa.Column("substitute_teacher_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("recommendation_rank", sa.Integer()),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("eligibility_facts", sa.JSON(), nullable=False),
        sa.Column("manual_override", sa.Boolean(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("assigned_by", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["need_id"], ["substitution_needs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["substitute_teacher_id"], ["teachers.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('active','cancelled')"),
        sa.CheckConstraint("score >= 0"),
    )
    for table, columns in {
        "waiting_policies": ("tenant_id", "timetable_project_id"),
        "teacher_waiting_profiles": ("tenant_id", "timetable_project_id", "teacher_id"),
        "teacher_absences": (
            "tenant_id",
            "timetable_project_id",
            "working_timetable_id",
            "school_id",
            "teacher_id",
            "absence_date",
            "status",
        ),
        "substitution_needs": (
            "tenant_id",
            "absence_id",
            "working_timetable_entry_id",
            "occurrence_id",
            "absent_teacher_id",
            "school_id",
            "subject_id",
            "status",
        ),
        "substitution_assignments": ("tenant_id", "need_id", "substitute_teacher_id", "status"),
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index(
        "uq_active_substitution_per_need",
        "substitution_assignments",
        ["tenant_id", "need_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    for table in (
        "substitution_assignments",
        "substitution_needs",
        "teacher_absences",
        "teacher_waiting_profiles",
        "waiting_policies",
    ):
        op.drop_table(table)
