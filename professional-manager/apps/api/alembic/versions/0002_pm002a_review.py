"""Enforce one current academic year per school.

Revision ID: 0002_pm002a_review
Revises: 0001_foundation
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_pm002a_review"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve the newest current year if an older PM-002A database contains duplicates.
    op.execute(
        sa.text(
            """
            UPDATE academic_years SET is_current = false
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY tenant_id, school_id
                        ORDER BY starts_on DESC, id DESC
                    ) AS position
                    FROM academic_years
                    WHERE is_current = true
                ) ranked
                WHERE position > 1
            )
            """
        )
    )
    op.create_index(
        "uq_academic_year_current_per_school",
        "academic_years",
        ["tenant_id", "school_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
        sqlite_where=sa.text("is_current = 1"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_academic_year_current_per_school", table_name="academic_years"
    )
