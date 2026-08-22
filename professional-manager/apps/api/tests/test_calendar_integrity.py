import uuid
from datetime import time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PeriodTemplate, WeekPattern
from conftest import FIRST_SCHOOL, SECOND_SCHOOL, TEST_TENANT


def test_period_template_requires_matching_school_week_pattern(session: Session) -> None:
    pattern = WeekPattern(
        tenant_id=uuid.UUID(TEST_TENANT),
        school_id=uuid.UUID(FIRST_SCHOOL),
        code="A",
        name_ar="الأسبوع أ",
        cycle_week_index=0,
    )
    session.add(pattern)
    session.flush()
    session.add(
        PeriodTemplate(
            tenant_id=uuid.UUID(TEST_TENANT),
            school_id=uuid.UUID(SECOND_SCHOOL),
            week_pattern_id=pattern.id,
            day_code="sun",
            period_number=1,
            starts_at=time(8, 0),
            ends_at=time(8, 45),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cycle_week_index_is_unique_per_school(session: Session) -> None:
    session.add_all(
        [
            WeekPattern(
                tenant_id=uuid.UUID(TEST_TENANT),
                school_id=uuid.UUID(FIRST_SCHOOL),
                code=code,
                name_ar=f"الأسبوع {code}",
                cycle_week_index=0,
            )
            for code in ("A", "B")
        ]
    )
    with pytest.raises(IntegrityError):
        session.flush()
