"""Normalize term-scoped teaching assignments.

Revision ID: 0004_pm002c_assignments
Revises: 0003_pm002b_master_data
"""

import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0004_pm002c_assignments"
down_revision = "0003_pm002b_master_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "section_offerings" not in tables:
        _create_section_offerings()

    columns = {item["name"] for item in sa.inspect(bind).get_columns("teaching_assignments")}
    if "term_id" not in columns:
        with op.batch_alter_table("teaching_assignments") as batch:
            batch.add_column(sa.Column("term_id", sa.Uuid(), nullable=True))
            batch.add_column(sa.Column("notes", sa.String(300), nullable=True))
            batch.create_foreign_key(
                "fk_assignment_term", "terms", ["term_id"], ["id"], ondelete="CASCADE"
            )
        _backfill_legacy_assignments(bind)
        missing = bind.execute(
            sa.text("SELECT COUNT(*) FROM teaching_assignments WHERE term_id IS NULL")
        ).scalar_one()
        if missing:
            raise RuntimeError(
                "Legacy teaching assignments require a valid school term before PM-002C migration"
            )
        with op.batch_alter_table("teaching_assignments") as batch:
            batch.alter_column("term_id", nullable=False)
            batch.create_check_constraint("ck_assignment_weekly_positive", "weekly_occurrences > 0")

    tables = set(sa.inspect(bind).get_table_names())
    if "teaching_assignment_sections" not in tables:
        _create_assignment_sections()
    if "teaching_assignment_resources" not in tables:
        _create_assignment_resources()

    columns = {item["name"] for item in sa.inspect(bind).get_columns("teaching_assignments")}
    if "section_ids" in columns or "resource_ids" in columns:
        _backfill_legacy_relations(bind)
        with op.batch_alter_table("teaching_assignments") as batch:
            if "section_ids" in columns:
                batch.drop_column("section_ids")
            if "resource_ids" in columns:
                batch.drop_column("resource_ids")


def _create_section_offerings() -> None:
    op.create_table(
        "section_offerings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("term_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shift_id"], ["school_shifts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "school_id", "term_id", "section_id", name="uq_section_offering"
        ),
    )
    for column in ("school_id", "term_id", "section_id", "shift_id"):
        op.create_index(f"ix_section_offerings_{column}", "section_offerings", [column])


def _create_assignment_sections() -> None:
    op.create_table(
        "teaching_assignment_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("teaching_assignment_id", sa.Uuid(), nullable=False),
        sa.Column("section_offering_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["teaching_assignment_id"], ["teaching_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["section_offering_id"], ["section_offerings.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "teaching_assignment_id",
            "section_offering_id",
            name="uq_assignment_section",
        ),
    )
    op.create_index(
        "ix_assignment_sections_assignment",
        "teaching_assignment_sections",
        ["teaching_assignment_id"],
    )
    op.create_index(
        "ix_assignment_sections_offering",
        "teaching_assignment_sections",
        ["section_offering_id"],
    )


def _create_assignment_resources() -> None:
    op.create_table(
        "teaching_assignment_resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("teaching_assignment_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["teaching_assignment_id"], ["teaching_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "teaching_assignment_id",
            "resource_id",
            name="uq_assignment_resource",
        ),
    )
    op.create_index(
        "ix_assignment_resources_assignment",
        "teaching_assignment_resources",
        ["teaching_assignment_id"],
    )
    op.create_index(
        "ix_assignment_resources_resource",
        "teaching_assignment_resources",
        ["resource_id"],
    )


def _backfill_legacy_assignments(bind: sa.Connection) -> None:
    rows = bind.execute(sa.text("SELECT id, school_id FROM teaching_assignments")).mappings()
    for row in rows:
        term_id = bind.execute(
            sa.text(
                "SELECT t.id FROM terms t JOIN academic_years y ON y.id=t.academic_year_id "
                "WHERE y.school_id=:school_id ORDER BY y.is_current DESC, y.starts_on DESC, t.order "
                "LIMIT 1"
            ),
            {"school_id": row["school_id"]},
        ).scalar_one_or_none()
        if term_id:
            bind.execute(
                sa.text("UPDATE teaching_assignments SET term_id=:term WHERE id=:assignment"),
                {"term": term_id, "assignment": row["id"]},
            )


def _backfill_legacy_relations(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.text(
            "SELECT id, tenant_id, school_id, term_id, section_ids, resource_ids "
            "FROM teaching_assignments"
        )
    ).mappings()
    for row in rows:
        section_ids = _json_ids(row["section_ids"])
        resource_ids = _json_ids(row["resource_ids"])
        shift_id = bind.execute(
            sa.text(
                "SELECT id FROM school_shifts WHERE tenant_id=:tenant AND school_id=:school "
                'AND is_active=true ORDER BY "order" LIMIT 1'
            ),
            {"tenant": row["tenant_id"], "school": row["school_id"]},
        ).scalar_one_or_none()
        for section_id in section_ids:
            if not shift_id:
                continue
            offering_id = uuid.uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO section_offerings "
                    "(id, tenant_id, school_id, term_id, section_id, shift_id, is_active, created_at, updated_at) "
                    "VALUES (:id,:tenant,:school,:term,:section,:shift,true,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) "
                    "ON CONFLICT (tenant_id,school_id,term_id,section_id) DO NOTHING"
                ),
                {
                    "id": offering_id,
                    "tenant": row["tenant_id"],
                    "school": row["school_id"],
                    "term": row["term_id"],
                    "section": section_id,
                    "shift": shift_id,
                },
            )
            actual = bind.execute(
                sa.text(
                    "SELECT id FROM section_offerings WHERE tenant_id=:tenant AND school_id=:school "
                    "AND term_id=:term AND section_id=:section"
                ),
                {
                    "tenant": row["tenant_id"],
                    "school": row["school_id"],
                    "term": row["term_id"],
                    "section": section_id,
                },
            ).scalar_one()
            bind.execute(
                sa.text(
                    "INSERT INTO teaching_assignment_sections "
                    "(id,tenant_id,teaching_assignment_id,section_offering_id) "
                    "VALUES (:id,:tenant,:assignment,:offering)"
                ),
                {
                    "id": uuid.uuid4(),
                    "tenant": row["tenant_id"],
                    "assignment": row["id"],
                    "offering": actual,
                },
            )
        for resource_id in resource_ids:
            bind.execute(
                sa.text(
                    "INSERT INTO teaching_assignment_resources "
                    "(id,tenant_id,teaching_assignment_id,resource_id) "
                    "VALUES (:id,:tenant,:assignment,:resource)"
                ),
                {
                    "id": uuid.uuid4(),
                    "tenant": row["tenant_id"],
                    "assignment": row["id"],
                    "resource": resource_id,
                },
            )


def _json_ids(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return [str(item) for item in parsed] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def downgrade() -> None:
    op.drop_table("teaching_assignment_resources")
    op.drop_table("teaching_assignment_sections")
    with op.batch_alter_table("teaching_assignments") as batch:
        batch.add_column(sa.Column("resource_ids", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("section_ids", sa.JSON(), nullable=False, server_default="[]"))
        batch.drop_column("notes")
        batch.drop_column("term_id")
    op.drop_table("section_offerings")
