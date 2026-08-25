"""Create the PM-001 foundation and PM-002A school-setup schema.

Includes canonical tenant teachers, relational teacher-school memberships,
relational teaching-assignment teachers, and multi-school project scopes.
Calendar slots are school/week-pattern scoped and project terms are selected per school.
PM-002A adds academic date bounds, shifts, school days, flexible academic hierarchy,
and ordered teaching/non-teaching day blocks. Metadata is intentionally evaluated at
migration time while the foundation branch remains unreleased, so a clean upgrade
creates the complete reviewed baseline without a lossy transitional migration.

Revision ID: 0001_foundation
"""
from alembic import op

from app.db import Base
from app import models  # noqa: F401

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
