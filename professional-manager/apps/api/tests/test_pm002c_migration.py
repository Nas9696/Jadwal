import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


def migration_module() -> ModuleType:
    path = Path(__file__).parents[1] / "alembic" / "versions" / "0004_pm002c_assignments.py"
    spec = importlib.util.spec_from_file_location("pm002c_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_backfill_skips_cross_scope_sections_and_resources() -> None:
    engine = sa.create_engine("sqlite://")
    statements = [
        "CREATE TABLE stages (id TEXT PRIMARY KEY, tenant_id TEXT, school_id TEXT)",
        "CREATE TABLE grades (id TEXT PRIMARY KEY, tenant_id TEXT, stage_id TEXT)",
        "CREATE TABLE sections (id TEXT PRIMARY KEY, tenant_id TEXT, grade_id TEXT)",
        "CREATE TABLE resources (id TEXT PRIMARY KEY, tenant_id TEXT, school_id TEXT)",
        'CREATE TABLE school_shifts (id TEXT PRIMARY KEY, tenant_id TEXT, school_id TEXT, is_active BOOLEAN, "order" INTEGER)',
        "CREATE TABLE teaching_assignments (id TEXT PRIMARY KEY, tenant_id TEXT, school_id TEXT, term_id TEXT, section_ids TEXT, resource_ids TEXT)",
        "CREATE TABLE section_offerings (id TEXT PRIMARY KEY, tenant_id TEXT, school_id TEXT, term_id TEXT, section_id TEXT, shift_id TEXT, is_active BOOLEAN, created_at TEXT, updated_at TEXT, UNIQUE(tenant_id,school_id,term_id,section_id))",
        "CREATE TABLE teaching_assignment_sections (id TEXT PRIMARY KEY, tenant_id TEXT, teaching_assignment_id TEXT, section_offering_id TEXT)",
        "CREATE TABLE teaching_assignment_resources (id TEXT PRIMARY KEY, tenant_id TEXT, teaching_assignment_id TEXT, resource_id TEXT)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(sa.text(statement))
        connection.execute(sa.text("INSERT INTO stages VALUES ('stage-ok','tenant-a','school-a'),('stage-other','tenant-a','school-b')"))
        connection.execute(sa.text("INSERT INTO grades VALUES ('grade-ok','tenant-a','stage-ok'),('grade-other','tenant-a','stage-other')"))
        connection.execute(sa.text("INSERT INTO sections VALUES ('section-ok','tenant-a','grade-ok'),('section-other','tenant-a','grade-other')"))
        connection.execute(sa.text("INSERT INTO resources VALUES ('resource-ok','tenant-a','school-a'),('resource-other','tenant-a','school-b')"))
        connection.execute(sa.text("INSERT INTO school_shifts VALUES ('shift-a','tenant-a','school-a',1,0)"))
        connection.execute(
            sa.text(
                "INSERT INTO teaching_assignments VALUES "
                "('assignment-a','tenant-a','school-a','term-a',"
                "'[\"section-ok\",\"section-other\"]','[\"resource-ok\",\"resource-other\"]')"
            )
        )
        migration_module()._backfill_legacy_relations(connection)
        sections = connection.execute(
            sa.text("SELECT section_id FROM section_offerings")
        ).scalars().all()
        resources = connection.execute(
            sa.text("SELECT resource_id FROM teaching_assignment_resources")
        ).scalars().all()
    assert sections == ["section-ok"]
    assert resources == ["resource-ok"]
