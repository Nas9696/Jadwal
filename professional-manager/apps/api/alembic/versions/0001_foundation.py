"""Create corrected PM-001 foundation schema.

Includes canonical tenant teachers, relational teacher-school memberships,
relational teaching-assignment teachers, and multi-school project scopes.
Calendar slots are school/week-pattern scoped and project terms are selected per school.

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
