"""Add PM-002B teacher, curriculum and resource master data.

Revision ID: 0003_pm002b_master_data
Revises: 0002_pm002a_review
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_pm002b_master_data"
down_revision = "0002_pm002a_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 0001 intentionally evaluates current metadata for clean installs.  The
    # guards below keep this transition useful for both a clean database (where the
    # PM-002B shape already exists) and databases created before PM-002B.
    bind = op.get_bind()

    def columns(table: str) -> set[str]:
        return {item["name"] for item in sa.inspect(bind).get_columns(table)}

    teacher_columns = columns("teachers")
    if "name_en" not in teacher_columns or "is_active" not in teacher_columns:
        with op.batch_alter_table("teachers") as batch:
            if "name_en" not in teacher_columns:
                batch.add_column(sa.Column("name_en", sa.String(200), nullable=True))
            if "is_active" not in teacher_columns:
                batch.add_column(
                    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
                )

    subject_columns = columns("subjects")
    if "is_active" not in subject_columns:
        with op.batch_alter_table("subjects") as batch:
            batch.add_column(
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
            )
    subject_unique_sets = {
        tuple(item["column_names"])
        for item in sa.inspect(bind).get_unique_constraints("subjects")
    }
    with op.batch_alter_table("subjects") as batch:
        if ("tenant_id", "school_id", "code") not in subject_unique_sets:
            batch.create_unique_constraint(
                "uq_subject_school_code", ["tenant_id", "school_id", "code"]
            )
        if ("tenant_id", "school_id", "name_ar") not in subject_unique_sets:
            batch.create_unique_constraint(
                "uq_subject_school_name", ["tenant_id", "school_id", "name_ar"]
            )

    resource_columns = columns("resources")
    if "code" not in resource_columns:
        with op.batch_alter_table("resources") as batch:
            batch.add_column(sa.Column("code", sa.String(50), nullable=True))
        op.execute(
            sa.text(
                "UPDATE resources SET code = 'RES-' || substr(CAST(id AS VARCHAR), 1, 8) "
                "WHERE code IS NULL"
            )
        )
        with op.batch_alter_table("resources") as batch:
            batch.alter_column("code", nullable=False)
    if "is_active" not in resource_columns:
        with op.batch_alter_table("resources") as batch:
            batch.add_column(
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
            )
    resource_unique_sets = {
        tuple(item["column_names"])
        for item in sa.inspect(bind).get_unique_constraints("resources")
    }
    if ("tenant_id", "school_id", "code") not in resource_unique_sets:
        with op.batch_alter_table("resources") as batch:
            batch.create_unique_constraint(
                "uq_resource_school_code", ["tenant_id", "school_id", "code"]
            )

    if "curriculum_requirements" not in sa.inspect(bind).get_table_names():
        _create_curriculum_table()

    membership_indexes = {
        item["name"] for item in sa.inspect(bind).get_indexes("teacher_school_memberships")
    }
    if "uq_teacher_active_home_school" not in membership_indexes:
        op.create_index(
            "uq_teacher_active_home_school",
            "teacher_school_memberships",
            ["tenant_id", "teacher_id"],
            unique=True,
            postgresql_where=sa.text("is_home_school = true AND is_active = true"),
            sqlite_where=sa.text("is_home_school = 1 AND is_active = 1"),
        )


def _create_curriculum_table() -> None:
    op.create_table(
        "curriculum_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("grade_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("weekly_occurrences", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("weekly_occurrences > 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grade_id"], ["grades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "school_id", "grade_id", "subject_id", name="uq_curriculum_grade_subject"
        ),
    )
    op.create_index("ix_curriculum_school", "curriculum_requirements", ["school_id"])
    op.create_index("ix_curriculum_grade", "curriculum_requirements", ["grade_id"])
    op.create_index("ix_curriculum_subject", "curriculum_requirements", ["subject_id"])


def downgrade() -> None:
    op.drop_index("uq_teacher_active_home_school", table_name="teacher_school_memberships")
    op.drop_table("curriculum_requirements")
    op.drop_constraint("uq_resource_school_code", "resources", type_="unique")
    op.drop_column("resources", "is_active")
    op.drop_column("resources", "code")
    op.drop_constraint("uq_subject_school_name", "subjects", type_="unique")
    op.drop_constraint("uq_subject_school_code", "subjects", type_="unique")
    op.drop_column("subjects", "is_active")
    op.drop_column("teachers", "is_active")
    op.drop_column("teachers", "name_en")
