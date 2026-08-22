import uuid
from datetime import date

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    AcademicYear,
    Resource,
    School,
    SchoolComplex,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    Tenant,
    TenantMembership,
    User,
    TimetableProject,
    TimetableProjectSchool,
)

DEMO_TENANT_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
DEMO_SCHOOL_ID = uuid.UUID("00000000-0000-4000-8000-000000000101")
DEMO_SECOND_SCHOOL_ID = uuid.UUID("00000000-0000-4000-8000-000000000102")
DEMO_COMPLEX_ID = uuid.UUID("00000000-0000-4000-8000-000000000011")
DEMO_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000201")

def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Tenant).where(Tenant.id == DEMO_TENANT_ID)):
            return
        db.add(Tenant(id=DEMO_TENANT_ID, name_ar="مجموعة مدارس الآفاق", name_en="Al Afaq Schools", slug="al-afaq"))
        db.add(User(id=DEMO_USER_ID, email="manager@example.test", display_name_ar="خالد العتيبي"))
        db.add(TenantMembership(tenant_id=DEMO_TENANT_ID, user_id=DEMO_USER_ID, role="manager", permissions=["school:read", "timetable:manage"]))
        db.add(SchoolComplex(id=DEMO_COMPLEX_ID, tenant_id=DEMO_TENANT_ID, name_ar="مجمع الآفاق التعليمي", name_en="Al Afaq Educational Complex", code="AFAQ"))
        db.add(School(id=DEMO_SCHOOL_ID, tenant_id=DEMO_TENANT_ID, complex_id=DEMO_COMPLEX_ID, name_ar="مدارس الآفاق", name_en="Al Afaq Schools", code="AFAQ-01", school_type="school"))
        db.add(School(id=DEMO_SECOND_SCHOOL_ID, tenant_id=DEMO_TENANT_ID, complex_id=DEMO_COMPLEX_ID, name_ar="ثانوية الآفاق", name_en="Al Afaq Secondary", code="AFAQ-02", school_type="school"))
        db.add(AcademicYear(tenant_id=DEMO_TENANT_ID, school_id=DEMO_SCHOOL_ID, name="1448 هـ", starts_on=date(2026, 8, 23), ends_on=date(2027, 6, 30)))
        teachers = []
        for code, name, specialty in [("T001", "أحمد العتيبي", "الرياضيات"), ("T002", "سارة القحطاني", "العلوم"), ("T003", "محمد الغامدي", "اللغة العربية")]:
            teacher = Teacher(tenant_id=DEMO_TENANT_ID, canonical_code=code, name_ar=name, specialty_reference=specialty)
            teachers.append(teacher)
            db.add(teacher)
        db.flush()
        for teacher in teachers:
            db.add(TeacherSchoolMembership(tenant_id=DEMO_TENANT_ID, teacher_id=teacher.id, school_id=DEMO_SCHOOL_ID, local_employee_code=teacher.canonical_code, is_home_school=True))
        db.add(TeacherSchoolMembership(tenant_id=DEMO_TENANT_ID, teacher_id=teachers[0].id, school_id=DEMO_SECOND_SCHOOL_ID, local_employee_code="SHARED-01"))
        for code, name in [("MATH", "الرياضيات"), ("SCI", "العلوم"), ("AR", "لغتي")]:
            db.add(Subject(tenant_id=DEMO_TENANT_ID, school_id=DEMO_SCHOOL_ID, code=code, name_ar=name))
        db.add(Resource(tenant_id=DEMO_TENANT_ID, school_id=DEMO_SCHOOL_ID, name_ar="مختبر العلوم", resource_type="lab", capacity=30))
        project = TimetableProject(tenant_id=DEMO_TENANT_ID, complex_id=DEMO_COMPLEX_ID, scope_type="complex", name_ar="جدول مجمع الآفاق")
        db.add(project)
        db.flush()
        for school_id in (DEMO_SCHOOL_ID, DEMO_SECOND_SCHOOL_ID):
            db.add(TimetableProjectSchool(tenant_id=DEMO_TENANT_ID, timetable_project_id=project.id, school_id=school_id))
        db.commit()

if __name__ == "__main__":
    seed()
