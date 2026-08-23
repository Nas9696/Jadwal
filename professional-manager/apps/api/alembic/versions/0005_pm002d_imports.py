"""Add staged smart-import jobs and rows.

Revision ID: 0005_pm002d_imports
Revises: 0004_pm002c_assignments
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_pm002d_imports"
down_revision = "0004_pm002c_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    existing = {"import_jobs", "import_rows"} & tables
    # Revision 0001 intentionally evaluates the current reviewed metadata on a
    # clean installation. In that path PM-002D tables already exist when the
    # revision chain reaches 0005, while older deployed databases need both.
    if existing == {"import_jobs", "import_rows"}:
        return
    if existing:
        raise RuntimeError("Incomplete PM-002D import staging schema")
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("term_id", sa.Uuid(), nullable=True),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("detected_sheets", sa.JSON(), nullable=False),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("validation_summary", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("duplicate_file_warning", sa.Boolean(), nullable=False),
        sa.Column("actor_reference", sa.String(200), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("file_size >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("tenant_id", "school_id", "term_id", "file_sha256", "status"):
        op.create_index(f"ix_import_jobs_{column}", "import_jobs", [column])
    op.create_table(
        "import_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("sheet_name", sa.String(150), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("source_values", sa.JSON(), nullable=False),
        sa.Column("normalized_values", sa.JSON(), nullable=False),
        sa.Column("proposed_action", sa.String(30), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("before_values", sa.JSON(), nullable=False),
        sa.Column("after_values", sa.JSON(), nullable=False),
        sa.Column("excluded", sa.Boolean(), nullable=False),
        sa.Column("group_key", sa.String(120), nullable=True),
        sa.CheckConstraint("source_row_number > 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_job_id"], ["import_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "import_job_id", "sheet_name", "source_row_number",
            name="uq_import_source_row",
        ),
    )
    for column in ("tenant_id", "import_job_id", "entity_type"):
        op.create_index(f"ix_import_rows_{column}", "import_rows", [column])


def downgrade() -> None:
    op.drop_table("import_rows")
    op.drop_table("import_jobs")
