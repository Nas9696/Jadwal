import uuid
from datetime import date, time

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    AcademicYear,
    CurriculumRequirement,
    Grade,
    PeriodTemplate,
    Resource,
    Section,
    SectionOffering,
    School,
    SchoolComplex,
    SchoolDay,
    SchoolShift,
    Stage,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentResource,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    Term,
    Tenant,
    TenantMembership,
    User,
    TimetableProject,
    TimetableProjectSchool,
    WaitingPolicy,
    WeekPattern,
)

DEMO_TENANT_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
DEMO_SCHOOL_ID = uuid.UUID("00000000-0000-4000-8000-000000000101")
DEMO_SECOND_SCHOOL_ID = uuid.UUID("00000000-0000-4000-8000-000000000102")
DEMO_COMPLEX_ID = uuid.UUID("00000000-0000-4000-8000-000000000011")
DEMO_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000201")
DEMO_FIRST_YEAR_ID = uuid.UUID("00000000-0000-4000-8000-000000000301")
DEMO_SECOND_YEAR_ID = uuid.UUID("00000000-0000-4000-8000-000000000302")
DEMO_FIRST_TERM_ID = uuid.UUID("00000000-0000-4000-8000-000000000401")
DEMO_SECOND_TERM_ID = uuid.UUID("00000000-0000-4000-8000-000000000402")


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Tenant).where(Tenant.id == DEMO_TENANT_ID)):
            return
        db.add(
            Tenant(
                id=DEMO_TENANT_ID,
                name_ar="مجموعة مدارس الآفاق",
                name_en="Al Afaq Schools",
                slug="al-afaq",
            )
        )
        db.add(User(id=DEMO_USER_ID, email="manager@example.test", display_name_ar="خالد العتيبي"))
        db.flush()
        db.add(
            TenantMembership(
                tenant_id=DEMO_TENANT_ID,
                user_id=DEMO_USER_ID,
                role="manager",
                permissions=["school:read", "timetable:manage"],
            )
        )
        db.add(
            SchoolComplex(
                id=DEMO_COMPLEX_ID,
                tenant_id=DEMO_TENANT_ID,
                name_ar="مجمع الآفاق التعليمي",
                name_en="Al Afaq Educational Complex",
                code="AFAQ",
            )
        )
        db.flush()
        db.add(
            School(
                id=DEMO_SCHOOL_ID,
                tenant_id=DEMO_TENANT_ID,
                complex_id=DEMO_COMPLEX_ID,
                name_ar="مدارس الآفاق",
                name_en="Al Afaq Schools",
                code="AFAQ-01",
                school_type="school",
            )
        )
        db.add(
            School(
                id=DEMO_SECOND_SCHOOL_ID,
                tenant_id=DEMO_TENANT_ID,
                complex_id=DEMO_COMPLEX_ID,
                name_ar="ثانوية الآفاق",
                name_en="Al Afaq Secondary",
                code="AFAQ-02",
                school_type="school",
            )
        )
        db.flush()
        for year_id, school_id in (
            (DEMO_FIRST_YEAR_ID, DEMO_SCHOOL_ID),
            (DEMO_SECOND_YEAR_ID, DEMO_SECOND_SCHOOL_ID),
        ):
            db.add(
                AcademicYear(
                    id=year_id,
                    tenant_id=DEMO_TENANT_ID,
                    school_id=school_id,
                    name="1448 هـ",
                    starts_on=date(2026, 8, 23),
                    ends_on=date(2027, 6, 30),
                )
            )
        db.flush()
        db.add(
            Term(
                id=DEMO_FIRST_TERM_ID,
                tenant_id=DEMO_TENANT_ID,
                academic_year_id=DEMO_FIRST_YEAR_ID,
                name_ar="الفصل الأول",
                order=1,
                starts_on=date(2026, 8, 23),
                ends_on=date(2026, 12, 31),
            )
        )
        db.add(
            Term(
                id=DEMO_SECOND_TERM_ID,
                tenant_id=DEMO_TENANT_ID,
                academic_year_id=DEMO_SECOND_YEAR_ID,
                name_ar="الفصل الأول",
                order=1,
                starts_on=date(2026, 8, 23),
                ends_on=date(2026, 12, 31),
            )
        )
        db.flush()
        shift = SchoolShift(
            tenant_id=DEMO_TENANT_ID, school_id=DEMO_SCHOOL_ID, code="AM", name_ar="صباحي", order=0
        )
        db.add(shift)
        patterns = []
        for school_id in (DEMO_SCHOOL_ID, DEMO_SECOND_SCHOOL_ID):
            for cycle_index, code in enumerate(("A", "B", "C")):
                pattern = WeekPattern(
                    tenant_id=DEMO_TENANT_ID,
                    school_id=school_id,
                    code=code,
                    name_ar=f"الأسبوع {code}",
                    cycle_week_index=cycle_index,
                )
                patterns.append(pattern)
                db.add(pattern)
        db.flush()
        for pattern in patterns[:3]:
            day = SchoolDay(
                tenant_id=DEMO_TENANT_ID,
                school_id=DEMO_SCHOOL_ID,
                shift_id=shift.id,
                week_pattern_id=pattern.id,
                weekday_index=0,
                label_ar="الأحد",
            )
            db.add(day)
            db.flush()
            for index, hour in enumerate((8, 9, 10, 11), 1):
                db.add(
                    PeriodTemplate(
                        tenant_id=DEMO_TENANT_ID,
                        school_id=DEMO_SCHOOL_ID,
                        shift_id=shift.id,
                        school_day_id=day.id,
                        week_pattern_id=pattern.id,
                        weekday_index=0,
                        block_order=index,
                        period_number=index,
                        label_ar=f"الحصة {index}",
                        starts_at=time(hour, 0),
                        ends_at=time(hour, 45),
                        block_type="lesson",
                        schedulable=True,
                    )
                )
        teachers = []
        for code, name, specialty in [
            ("T001", "أحمد العتيبي", "الرياضيات"),
            ("T002", "سارة القحطاني", "العلوم"),
            ("T003", "محمد الغامدي", "اللغة العربية"),
        ]:
            teacher = Teacher(
                tenant_id=DEMO_TENANT_ID,
                canonical_code=code,
                name_ar=name,
                specialty_reference=specialty,
            )
            teachers.append(teacher)
            db.add(teacher)
        db.flush()
        for teacher in teachers:
            db.add(
                TeacherSchoolMembership(
                    tenant_id=DEMO_TENANT_ID,
                    teacher_id=teacher.id,
                    school_id=DEMO_SCHOOL_ID,
                    local_employee_code=teacher.canonical_code,
                    is_home_school=True,
                )
            )
        db.add(
            TeacherSchoolMembership(
                tenant_id=DEMO_TENANT_ID,
                teacher_id=teachers[0].id,
                school_id=DEMO_SECOND_SCHOOL_ID,
                local_employee_code="SHARED-01",
            )
        )
        subjects = []
        for code, name in [("MATH", "الرياضيات"), ("SCI", "العلوم"), ("AR", "لغتي")]:
            subject = Subject(
                tenant_id=DEMO_TENANT_ID, school_id=DEMO_SCHOOL_ID, code=code, name_ar=name
            )
            subjects.append(subject)
            db.add(subject)
        stage = Stage(
            tenant_id=DEMO_TENANT_ID,
            school_id=DEMO_SCHOOL_ID,
            code="INT",
            name_ar="المرحلة المتوسطة",
            order=0,
        )
        db.add(stage)
        db.flush()
        grade = Grade(tenant_id=DEMO_TENANT_ID, stage_id=stage.id, name_ar="الأول المتوسط", order=0)
        db.add(grade)
        db.flush()
        sections = [
            Section(tenant_id=DEMO_TENANT_ID, grade_id=grade.id, name_ar=name, capacity=30)
            for name in ("أ", "ب")
        ]
        db.add_all(sections)
        db.flush()
        offerings = [
            SectionOffering(
                tenant_id=DEMO_TENANT_ID,
                school_id=DEMO_SCHOOL_ID,
                term_id=DEMO_FIRST_TERM_ID,
                section_id=section.id,
                shift_id=shift.id,
                is_active=True,
            )
            for section in sections
        ]
        db.add_all(offerings)
        db.flush()
        db.add_all(
            CurriculumRequirement(
                tenant_id=DEMO_TENANT_ID,
                school_id=DEMO_SCHOOL_ID,
                grade_id=grade.id,
                subject_id=subject.id,
                weekly_occurrences=count,
            )
            for subject, count in zip(subjects, (6, 4, 6), strict=True)
        )
        resource = Resource(
            tenant_id=DEMO_TENANT_ID,
            school_id=DEMO_SCHOOL_ID,
            code="SCI-LAB",
            name_ar="مختبر العلوم",
            resource_type="science_lab",
            capacity=30,
        )
        db.add(resource)
        db.flush()
        assignment = TeachingAssignment(
            tenant_id=DEMO_TENANT_ID,
            school_id=DEMO_SCHOOL_ID,
            term_id=DEMO_FIRST_TERM_ID,
            subject_id=subjects[0].id,
            weekly_occurrences=3,
            notes="إسناد تجريبي جزئي",
            distribution={},
        )
        db.add(assignment)
        db.flush()
        db.add_all(
            [
                TeachingAssignmentTeacher(
                    tenant_id=DEMO_TENANT_ID,
                    teaching_assignment_id=assignment.id,
                    teacher_id=teachers[0].id,
                ),
                TeachingAssignmentSection(
                    tenant_id=DEMO_TENANT_ID,
                    teaching_assignment_id=assignment.id,
                    section_offering_id=offerings[0].id,
                ),
                TeachingAssignmentResource(
                    tenant_id=DEMO_TENANT_ID,
                    teaching_assignment_id=assignment.id,
                    resource_id=resource.id,
                ),
            ]
        )
        project = TimetableProject(
            tenant_id=DEMO_TENANT_ID,
            complex_id=DEMO_COMPLEX_ID,
            scope_type="complex",
            name_ar="جدول مجمع الآفاق",
        )
        db.add(project)
        db.flush()
        for school_id, term_id in (
            (DEMO_SCHOOL_ID, DEMO_FIRST_TERM_ID),
            (DEMO_SECOND_SCHOOL_ID, DEMO_SECOND_TERM_ID),
        ):
            db.add(
                TimetableProjectSchool(
                    tenant_id=DEMO_TENANT_ID,
                    timetable_project_id=project.id,
                    school_id=school_id,
                    term_id=term_id,
                )
            )
        db.add(
            WaitingPolicy(
                tenant_id=DEMO_TENANT_ID,
                timetable_project_id=project.id,
                combined_workload_limit=24,
                daily_waiting_limit=2,
                weekly_waiting_limit=5,
                fairness_weight=5,
                specialty_preference_enabled=True,
                specialty_preference_weight=2,
                same_school_preference_weight=1,
                exclude_exempt_teachers=True,
                enabled=True,
            )
        )
        db.commit()


if __name__ == "__main__":
    seed()
