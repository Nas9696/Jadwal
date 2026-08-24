from __future__ import annotations

import argparse
import uuid
from datetime import date, time

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    AcademicYear,
    CurriculumRequirement,
    Grade,
    PeriodTemplate,
    Resource,
    SchedulingRule,
    School,
    SchoolComplex,
    SchoolDay,
    SchoolShift,
    Section,
    SectionOffering,
    Stage,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeacherWaitingProfile,
    TeachingAssignment,
    TeachingAssignmentResource,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    Tenant,
    TenantMembership,
    Term,
    TimetableProject,
    TimetableProjectSchool,
    User,
    WaitingPolicy,
    WeekPattern,
)
from app.seed import (
    DEMO_COMPLEX_ID,
    DEMO_FIRST_TERM_ID,
    DEMO_FIRST_YEAR_ID,
    DEMO_SCHOOL_ID,
    DEMO_SECOND_SCHOOL_ID,
    DEMO_SECOND_TERM_ID,
    DEMO_SECOND_YEAR_ID,
    DEMO_TENANT_ID,
    DEMO_USER_ID,
)

DEMO_PROJECT_NAME = "مشروع UAT — الفصل الأول 1448"
DEMO_EMAIL = "manager@example.test"
WEEKDAYS = ("الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس")


def _remove_existing_demo(db: Session) -> None:
    # SQLite does not enable FK cascades by default. The production demo runs on
    # PostgreSQL, but keeping the reset path deterministic on SQLite makes local
    # smoke checks and tests exercise the same replacement lifecycle.
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        db.rollback()
        db.execute(text("PRAGMA foreign_keys = ON"))
    db.execute(delete(Tenant).where(Tenant.id == DEMO_TENANT_ID))
    db.flush()
    db.execute(delete(User).where((User.id == DEMO_USER_ID) | (User.email == DEMO_EMAIL)))
    db.commit()


def _calendar(
    db: Session, school_id: uuid.UUID, shift: SchoolShift, pattern: WeekPattern
) -> None:
    blocks = (
        ("الطابور الصباحي", time(6, 45), time(7, 0), "assembly", None, False),
        ("الحصة الأولى", time(7, 0), time(7, 45), "lesson", 1, True),
        ("الحصة الثانية", time(7, 45), time(8, 30), "lesson", 2, True),
        ("الفسحة", time(8, 30), time(8, 50), "break", None, False),
        ("الحصة الثالثة", time(8, 50), time(9, 35), "lesson", 3, True),
        ("الحصة الرابعة", time(9, 35), time(10, 20), "lesson", 4, True),
        ("الصلاة", time(10, 20), time(10, 40), "prayer", None, False),
        ("الحصة الخامسة", time(10, 40), time(11, 25), "lesson", 5, True),
        ("الحصة السادسة", time(11, 25), time(12, 10), "lesson", 6, True),
    )
    for weekday_index, weekday in enumerate(WEEKDAYS):
        day = SchoolDay(
            tenant_id=DEMO_TENANT_ID,
            school_id=school_id,
            shift_id=shift.id,
            week_pattern_id=pattern.id,
            weekday_index=weekday_index,
            label_ar=weekday,
        )
        db.add(day)
        db.flush()
        for order, (label, starts, ends, block_type, number, schedulable) in enumerate(
            blocks, 1
        ):
            db.add(
                PeriodTemplate(
                    tenant_id=DEMO_TENANT_ID,
                    school_id=school_id,
                    shift_id=shift.id,
                    school_day_id=day.id,
                    week_pattern_id=pattern.id,
                    weekday_index=weekday_index,
                    block_order=order,
                    period_number=number,
                    label_ar=label,
                    starts_at=starts,
                    ends_at=ends,
                    block_type=block_type,
                    attendance_mode="onsite",
                    schedulable=schedulable,
                )
            )


def _academic_structure(
    db: Session,
    school_id: uuid.UUID,
    term_id: uuid.UUID,
    shift_id: uuid.UUID,
    stage_code: str,
    stage_name: str,
    grade_names: tuple[str, ...],
) -> tuple[list[Grade], list[SectionOffering]]:
    stage = Stage(
        tenant_id=DEMO_TENANT_ID,
        school_id=school_id,
        code=stage_code,
        name_ar=stage_name,
        order=0,
    )
    db.add(stage)
    db.flush()
    grades: list[Grade] = []
    offerings: list[SectionOffering] = []
    for grade_order, grade_name in enumerate(grade_names):
        grade = Grade(
            tenant_id=DEMO_TENANT_ID,
            stage_id=stage.id,
            name_ar=grade_name,
            order=grade_order,
        )
        db.add(grade)
        db.flush()
        grades.append(grade)
        for section_name in ("أ", "ب"):
            section = Section(
                tenant_id=DEMO_TENANT_ID,
                grade_id=grade.id,
                name_ar=f"{grade_name} — {section_name}",
                capacity=30,
            )
            db.add(section)
            db.flush()
            offering = SectionOffering(
                tenant_id=DEMO_TENANT_ID,
                school_id=school_id,
                term_id=term_id,
                section_id=section.id,
                shift_id=shift_id,
                is_active=True,
            )
            db.add(offering)
            offerings.append(offering)
    db.flush()
    return grades, offerings


def _assignment(
    db: Session,
    *,
    school_id: uuid.UUID,
    term_id: uuid.UUID,
    subject: Subject,
    weekly: int,
    teachers: list[Teacher],
    offerings: list[SectionOffering],
    note: str,
    resource: Resource | None = None,
) -> TeachingAssignment:
    row = TeachingAssignment(
        tenant_id=DEMO_TENANT_ID,
        school_id=school_id,
        term_id=term_id,
        subject_id=subject.id,
        weekly_occurrences=weekly,
        distribution={},
        notes=note,
    )
    db.add(row)
    db.flush()
    db.add_all(
        TeachingAssignmentTeacher(
            tenant_id=DEMO_TENANT_ID,
            teaching_assignment_id=row.id,
            teacher_id=teacher.id,
        )
        for teacher in teachers
    )
    db.add_all(
        TeachingAssignmentSection(
            tenant_id=DEMO_TENANT_ID,
            teaching_assignment_id=row.id,
            section_offering_id=offering.id,
        )
        for offering in offerings
    )
    if resource:
        db.add(
            TeachingAssignmentResource(
                tenant_id=DEMO_TENANT_ID,
                teaching_assignment_id=row.id,
                resource_id=resource.id,
            )
        )
    return row


def seed_demo(db: Session, *, reset: bool = False) -> dict[str, int | str]:
    existing_project = db.scalar(
        select(TimetableProject).where(
            TimetableProject.tenant_id == DEMO_TENANT_ID,
            TimetableProject.name_ar == DEMO_PROJECT_NAME,
        )
    )
    if existing_project and not reset:
        return {"status": "already_ready", "project_id": str(existing_project.id)}
    if db.get(Tenant, DEMO_TENANT_ID) or reset:
        _remove_existing_demo(db)

    tenant = Tenant(
        id=DEMO_TENANT_ID,
        name_ar="مجموعة مدارس الآفاق",
        name_en="Al Afaq Schools",
        slug="al-afaq-demo",
    )
    user = User(
        id=DEMO_USER_ID,
        email=DEMO_EMAIL,
        display_name_ar="مدير المدرسة التجريبية",
    )
    db.add_all([tenant, user])
    db.flush()
    db.add(
        TenantMembership(
            tenant_id=DEMO_TENANT_ID,
            user_id=DEMO_USER_ID,
            role="manager",
            permissions=["school:read", "school:manage", "timetable:manage"],
        )
    )
    complex_row = SchoolComplex(
        id=DEMO_COMPLEX_ID,
        tenant_id=DEMO_TENANT_ID,
        name_ar="مجمع الآفاق التعليمي",
        name_en="Al Afaq Educational Complex",
        code="AFAQ-UAT",
    )
    db.add(complex_row)
    db.flush()
    first_school = School(
        id=DEMO_SCHOOL_ID,
        tenant_id=DEMO_TENANT_ID,
        complex_id=DEMO_COMPLEX_ID,
        name_ar="متوسطة الآفاق",
        name_en="Al Afaq Intermediate",
        code="AFAQ-INT",
        school_type="school",
    )
    second_school = School(
        id=DEMO_SECOND_SCHOOL_ID,
        tenant_id=DEMO_TENANT_ID,
        complex_id=DEMO_COMPLEX_ID,
        name_ar="ثانوية الآفاق",
        name_en="Al Afaq Secondary",
        code="AFAQ-SEC",
        school_type="school",
    )
    db.add_all([first_school, second_school])
    db.flush()

    for year_id, term_id, school_id in (
        (DEMO_FIRST_YEAR_ID, DEMO_FIRST_TERM_ID, DEMO_SCHOOL_ID),
        (DEMO_SECOND_YEAR_ID, DEMO_SECOND_TERM_ID, DEMO_SECOND_SCHOOL_ID),
    ):
        year = AcademicYear(
            id=year_id,
            tenant_id=DEMO_TENANT_ID,
            school_id=school_id,
            name="1448 هـ",
            starts_on=date(2026, 8, 23),
            ends_on=date(2027, 6, 30),
            is_current=True,
        )
        db.add(year)
        db.flush()
        db.add(
            Term(
                id=term_id,
                tenant_id=DEMO_TENANT_ID,
                academic_year_id=year_id,
                name_ar="الفصل الدراسي الأول",
                order=1,
                starts_on=date(2026, 8, 23),
                ends_on=date(2026, 12, 31),
            )
        )
    db.flush()

    shifts: dict[uuid.UUID, SchoolShift] = {}
    patterns: dict[uuid.UUID, WeekPattern] = {}
    for school_id in (DEMO_SCHOOL_ID, DEMO_SECOND_SCHOOL_ID):
        shift = SchoolShift(
            tenant_id=DEMO_TENANT_ID,
            school_id=school_id,
            code="AM",
            name_ar="الفترة الصباحية",
            name_en="Morning",
            order=0,
        )
        pattern = WeekPattern(
            tenant_id=DEMO_TENANT_ID,
            school_id=school_id,
            code="A",
            name_ar="أسبوع واحد",
            cycle_week_index=0,
        )
        db.add_all([shift, pattern])
        db.flush()
        shifts[school_id] = shift
        patterns[school_id] = pattern
        _calendar(db, school_id, shift, pattern)

    first_grades, first_offerings = _academic_structure(
        db,
        DEMO_SCHOOL_ID,
        DEMO_FIRST_TERM_ID,
        shifts[DEMO_SCHOOL_ID].id,
        "INT",
        "المرحلة المتوسطة",
        ("الأول المتوسط", "الثاني المتوسط"),
    )
    second_grades, second_offerings = _academic_structure(
        db,
        DEMO_SECOND_SCHOOL_ID,
        DEMO_SECOND_TERM_ID,
        shifts[DEMO_SECOND_SCHOOL_ID].id,
        "SEC",
        "المرحلة الثانوية",
        ("الأول الثانوي",),
    )

    teacher_data = (
        ("T001", "أحمد العتيبي", "الرياضيات", DEMO_SCHOOL_ID),
        ("T002", "سارة القحطاني", "العلوم", DEMO_SCHOOL_ID),
        ("T003", "محمد الغامدي", "اللغة العربية", DEMO_SCHOOL_ID),
        ("T004", "نورة الشهري", "اللغة الإنجليزية", DEMO_SCHOOL_ID),
        ("T005", "خالد الزهراني", "الدراسات الإسلامية", DEMO_SCHOOL_ID),
        ("T006", "ريم الحربي", "الحاسب", DEMO_SCHOOL_ID),
        ("T007", "فيصل الدوسري", "الدراسات الاجتماعية", DEMO_SCHOOL_ID),
        ("T008", "ليلى المطيري", "التربية البدنية", DEMO_SCHOOL_ID),
        ("T009", "عبدالله القرني", "الرياضيات", DEMO_SECOND_SCHOOL_ID),
        ("T010", "هدى السبيعي", "العلوم", DEMO_SECOND_SCHOOL_ID),
        ("T011", "ماجد المالكي", "اللغة العربية", DEMO_SECOND_SCHOOL_ID),
        ("T012", "عبير العنزي", "اللغة الإنجليزية", DEMO_SECOND_SCHOOL_ID),
        ("T013", "عمر الشمري", "معلم احتياط", DEMO_SCHOOL_ID),
    )
    teachers: dict[str, Teacher] = {}
    for code, name, specialty, home_school in teacher_data:
        teacher = Teacher(
            tenant_id=DEMO_TENANT_ID,
            canonical_code=code,
            name_ar=name,
            specialty_reference=specialty,
            base_workload=24,
            teaching_workload_limit=24,
            is_active=True,
        )
        db.add(teacher)
        db.flush()
        teachers[code] = teacher
        db.add(
            TeacherSchoolMembership(
                tenant_id=DEMO_TENANT_ID,
                teacher_id=teacher.id,
                school_id=home_school,
                local_employee_code=code,
                is_home_school=True,
                is_active=True,
            )
        )
    db.add(
        TeacherSchoolMembership(
            tenant_id=DEMO_TENANT_ID,
            teacher_id=teachers["T001"].id,
            school_id=DEMO_SECOND_SCHOOL_ID,
            local_employee_code="SEC-T001",
            is_home_school=False,
            is_active=True,
        )
    )

    subject_labels = (
        ("MATH", "الرياضيات"),
        ("SCI", "العلوم"),
        ("AR", "اللغة العربية"),
        ("EN", "اللغة الإنجليزية"),
        ("ISL", "الدراسات الإسلامية"),
        ("COMP", "المهارات الرقمية"),
        ("SOC", "الدراسات الاجتماعية"),
        ("PE", "التربية البدنية"),
    )
    subjects: dict[tuple[uuid.UUID, str], Subject] = {}
    for school_id, allowed in (
        (DEMO_SCHOOL_ID, subject_labels),
        (DEMO_SECOND_SCHOOL_ID, subject_labels[:4]),
    ):
        for code, label in allowed:
            subject = Subject(
                tenant_id=DEMO_TENANT_ID,
                school_id=school_id,
                code=code,
                name_ar=label,
                is_active=True,
            )
            db.add(subject)
            subjects[(school_id, code)] = subject
    db.flush()

    science_lab = Resource(
        tenant_id=DEMO_TENANT_ID,
        school_id=DEMO_SCHOOL_ID,
        code="SCI-LAB-1",
        name_ar="مختبر العلوم الرئيسي",
        resource_type="science_lab",
        capacity=30,
        exclusive=True,
        is_active=True,
    )
    computer_lab = Resource(
        tenant_id=DEMO_TENANT_ID,
        school_id=DEMO_SCHOOL_ID,
        code="COMP-LAB-1",
        name_ar="معمل الحاسب",
        resource_type="computer_lab",
        capacity=28,
        exclusive=True,
        is_active=True,
    )
    secondary_lab = Resource(
        tenant_id=DEMO_TENANT_ID,
        school_id=DEMO_SECOND_SCHOOL_ID,
        code="SEC-SCI-LAB",
        name_ar="مختبر العلوم الثانوية",
        resource_type="science_lab",
        capacity=30,
        exclusive=True,
        is_active=True,
    )
    db.add_all([science_lab, computer_lab, secondary_lab])
    db.flush()

    for grade in first_grades:
        for code, weekly in (("MATH", 4), ("SCI", 3), ("AR", 4), ("EN", 3)):
            db.add(
                CurriculumRequirement(
                    tenant_id=DEMO_TENANT_ID,
                    school_id=DEMO_SCHOOL_ID,
                    grade_id=grade.id,
                    subject_id=subjects[(DEMO_SCHOOL_ID, code)].id,
                    weekly_occurrences=weekly,
                    notes="نصاب UAT واقعي",
                )
            )
    for code, weekly in (("MATH", 4), ("SCI", 3), ("AR", 4), ("EN", 3)):
        db.add(
            CurriculumRequirement(
                tenant_id=DEMO_TENANT_ID,
                school_id=DEMO_SECOND_SCHOOL_ID,
                grade_id=second_grades[0].id,
                subject_id=subjects[(DEMO_SECOND_SCHOOL_ID, code)].id,
                weekly_occurrences=weekly,
                notes="نصاب UAT واقعي",
            )
        )

    first_a, first_b, second_a, second_b = first_offerings
    sec_a, sec_b = second_offerings
    assignments: dict[str, TeachingAssignment] = {}

    def add(key: str, **values: object) -> None:
        assignments[key] = _assignment(db, **values)  # type: ignore[arg-type]

    base = {"school_id": DEMO_SCHOOL_ID, "term_id": DEMO_FIRST_TERM_ID}
    add("MATH-1A", **base, subject=subjects[(DEMO_SCHOOL_ID, "MATH")], weekly=4, teachers=[teachers["T001"]], offerings=[first_a], note="رياضيات الأول أ")
    add("MATH-1B", **base, subject=subjects[(DEMO_SCHOOL_ID, "MATH")], weekly=4, teachers=[teachers["T001"]], offerings=[first_b], note="رياضيات الأول ب")
    add("SCI-1A", **base, subject=subjects[(DEMO_SCHOOL_ID, "SCI")], weekly=3, teachers=[teachers["T002"]], offerings=[first_a], resource=science_lab, note="علوم مخبرية")
    add("SCI-1B", **base, subject=subjects[(DEMO_SCHOOL_ID, "SCI")], weekly=3, teachers=[teachers["T002"]], offerings=[first_b], resource=science_lab, note="علوم مخبرية")
    add("AR-COMBINED", **base, subject=subjects[(DEMO_SCHOOL_ID, "AR")], weekly=2, teachers=[teachers["T003"]], offerings=[first_a, first_b], note="شعبتان مجمعتان")
    add("AR-1A", **base, subject=subjects[(DEMO_SCHOOL_ID, "AR")], weekly=2, teachers=[teachers["T003"]], offerings=[first_a], note="استكمال النصاب")
    add("AR-1B", **base, subject=subjects[(DEMO_SCHOOL_ID, "AR")], weekly=2, teachers=[teachers["T003"]], offerings=[first_b], note="استكمال النصاب")
    add("EN-1A", **base, subject=subjects[(DEMO_SCHOOL_ID, "EN")], weekly=3, teachers=[teachers["T004"]], offerings=[first_a], note="لغة إنجليزية")
    add("EN-1B", **base, subject=subjects[(DEMO_SCHOOL_ID, "EN")], weekly=3, teachers=[teachers["T004"]], offerings=[first_b], note="لغة إنجليزية")
    add("ISL-2A", **base, subject=subjects[(DEMO_SCHOOL_ID, "ISL")], weekly=3, teachers=[teachers["T005"]], offerings=[second_a], note="دراسات إسلامية")
    add("COMP-2A", **base, subject=subjects[(DEMO_SCHOOL_ID, "COMP")], weekly=2, teachers=[teachers["T006"]], offerings=[second_a], resource=computer_lab, note="مجموعة مهارات رقمية")
    add("COMP-2B", **base, subject=subjects[(DEMO_SCHOOL_ID, "COMP")], weekly=2, teachers=[teachers["T006"]], offerings=[second_b], resource=computer_lab, note="مجموعة مهارات رقمية")
    add("SOC-CO", **base, subject=subjects[(DEMO_SCHOOL_ID, "SOC")], weekly=2, teachers=[teachers["T007"], teachers["T008"]], offerings=[second_b], note="تدريس مشترك Co-teaching")
    add("PE-2A", **base, subject=subjects[(DEMO_SCHOOL_ID, "PE")], weekly=2, teachers=[teachers["T008"]], offerings=[second_a], note="تربية بدنية")

    secondary = {"school_id": DEMO_SECOND_SCHOOL_ID, "term_id": DEMO_SECOND_TERM_ID}
    add("SEC-MATH-A", **secondary, subject=subjects[(DEMO_SECOND_SCHOOL_ID, "MATH")], weekly=4, teachers=[teachers["T001"]], offerings=[sec_a], note="المعلم المشترك في الثانوية")
    add("SEC-MATH-B", **secondary, subject=subjects[(DEMO_SECOND_SCHOOL_ID, "MATH")], weekly=4, teachers=[teachers["T009"]], offerings=[sec_b], note="رياضيات الثانوية")
    add("SEC-SCI-A", **secondary, subject=subjects[(DEMO_SECOND_SCHOOL_ID, "SCI")], weekly=3, teachers=[teachers["T010"]], offerings=[sec_a], resource=secondary_lab, note="علوم الثانوية")
    add("SEC-AR-B", **secondary, subject=subjects[(DEMO_SECOND_SCHOOL_ID, "AR")], weekly=4, teachers=[teachers["T011"]], offerings=[sec_b], note="لغة عربية")
    add("SEC-EN-A", **secondary, subject=subjects[(DEMO_SECOND_SCHOOL_ID, "EN")], weekly=3, teachers=[teachers["T012"]], offerings=[sec_a], note="لغة إنجليزية")
    db.flush()

    project = TimetableProject(
        tenant_id=DEMO_TENANT_ID,
        complex_id=DEMO_COMPLEX_ID,
        scope_type="complex",
        name_ar=DEMO_PROJECT_NAME,
        description="مشروع جاهز لفحص Preflight وتوليد ثلاثة بدائل فعلية.",
        status="ready",
        settings={"optimization_profile": "balanced", "project_cycle_limit": 12},
    )
    db.add(project)
    db.flush()
    db.add_all(
        [
            TimetableProjectSchool(
                tenant_id=DEMO_TENANT_ID,
                timetable_project_id=project.id,
                school_id=DEMO_SCHOOL_ID,
                term_id=DEMO_FIRST_TERM_ID,
                cycle_phase_offset=0,
            ),
            TimetableProjectSchool(
                tenant_id=DEMO_TENANT_ID,
                timetable_project_id=project.id,
                school_id=DEMO_SECOND_SCHOOL_ID,
                term_id=DEMO_SECOND_TERM_ID,
                cycle_phase_offset=0,
            ),
        ]
    )
    rules: tuple[
        tuple[str, str, str, int | None, dict[str, str], dict[str, int]], ...
    ] = (
        ("حد أحمد اليومي", "teacher_max_lessons_per_day", "hard", None, {"teacher_id": str(teachers["T001"].id)}, {"maximum": 4}),
        ("رياضيات الأول أ على ثلاثة أيام", "assignment_min_days", "soft", 18, {"assignment_id": str(assignments["MATH-1A"].id)}, {"minimum_days": 3}),
        ("عدم تكرار رياضيات الأول أ يوميًا", "assignment_max_per_day", "hard", None, {"assignment_id": str(assignments["MATH-1A"].id)}, {"maximum": 2}),
        ("تفضيل العلوم قبل الظهر", "subject_preferred_time", "soft", 12, {"subject_id": str(subjects[(DEMO_SCHOOL_ID, "SCI")].id)}, {"starts_at_minute": 450, "ends_at_minute": 650}),
        ("تجنب رياضيات الحصة الأخيرة", "subject_avoided_time", "soft", 10, {"subject_id": str(subjects[(DEMO_SCHOOL_ID, "MATH")].id)}, {"starts_at_minute": 715, "ends_at_minute": 760}),
        ("عدم توفر سارة يوم الخميس", "teacher_unavailable", "hard", None, {"teacher_id": str(teachers["T002"].id)}, {"weekday_index": 4}),
        ("تجنب تتابع الحاسب", "assignment_forbid_consecutive", "soft", 8, {"assignment_id": str(assignments["COMP-2A"].id)}, {}),
    )
    db.add_all(
        SchedulingRule(
            tenant_id=DEMO_TENANT_ID,
            timetable_project_id=project.id,
            label=label,
            description="قاعدة Demo قابلة للفحص من الواجهة",
            rule_type=rule_type,
            severity=severity,
            weight=weight,
            selector=selector,
            parameters=parameters,
            enabled=True,
        )
        for label, rule_type, severity, weight, selector, parameters in rules
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
    db.add(
        TeacherWaitingProfile(
            tenant_id=DEMO_TENANT_ID,
            timetable_project_id=project.id,
            teacher_id=teachers["T008"].id,
            exempt=True,
            notes="إعفاء تجريبي ظاهر في تقرير الانتظار",
        )
    )
    db.commit()
    return {
        "status": "reset" if reset else "created",
        "project_id": str(project.id),
        "schools": 2,
        "teachers": len(teachers),
        "assignments": len(assignments),
        "rules": len(rules),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the isolated Professional Manager UAT demo")
    parser.add_argument("--reset", action="store_true", help="Replace only the fixed demo tenant")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(seed_demo(db, reset=args.reset))


if __name__ == "__main__":
    main()
