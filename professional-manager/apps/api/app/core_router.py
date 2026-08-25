import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core_schemas import (
    AssignmentTransferInput,
    AvailabilityCopyInput,
    BulkTeachersInput,
    CurriculumPlanInput,
    DayBuilderInput,
    GenerateInput,
    OrderedIdsInput,
    PeriodEditInput,
    PresetRuleInput,
    QuickAssignmentInput,
    SimpleSectionInput,
    SimpleSubjectInput,
    SimpleTeacherInput,
    StructureInput,
    TeacherMergeInput,
    TeacherAvailabilityInput,
)
from app.core_services import (
    copy_availability,
    create_simple_subject,
    create_simple_teacher,
    create_simple_teachers,
    delete_simple_section,
    delete_simple_subject,
    delete_simple_teacher,
    deduplicate_teacher_assignments,
    edit_period,
    generate,
    merge_simple_teachers,
    quick_assignment,
    remove_quick_assignment,
    save_availability,
    save_day_builder,
    save_curriculum_plan,
    save_preset_rule,
    save_section_order,
    save_structure,
    save_subject_order,
    save_teacher_order,
    transfer_assignments,
    update_quick_assignment,
    update_simple_section,
    update_simple_subject,
    update_simple_teacher,
    workflow_snapshot,
)
from app.db import get_db
from app.tenant import tenant_context
from app.solve_services import execute_solve_run
from app.import_services import _parse_csv, _parse_xlsx, normalize_text


router = APIRouter(prefix="/api/v1/schools/{school_id}/core-workflow", tags=["core workflow"])


@router.get("")
def snapshot(school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(workflow_snapshot(db, tenant, school_id))


@router.put("/school-day")
def school_day(payload: DayBuilderInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_day_builder(db, tenant, school_id, payload))


@router.put("/periods/{block_id}")
def period(block_id: uuid.UUID, payload: PeriodEditInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(edit_period(db, tenant, school_id, block_id, payload))


@router.put("/structure")
def structure(payload: StructureInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_structure(db, tenant, school_id, payload))


@router.put("/teachers/{teacher_id}/availability")
def availability(teacher_id: uuid.UUID, payload: TeacherAvailabilityInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_availability(db, tenant, school_id, teacher_id, payload))


@router.post("/teachers", status_code=201)
def create_teacher(payload: SimpleTeacherInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(create_simple_teacher(db, tenant, school_id, payload))


@router.put("/teachers/{teacher_id}")
def update_teacher(teacher_id: uuid.UUID, payload: SimpleTeacherInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(update_simple_teacher(db, tenant, school_id, teacher_id, payload))


@router.delete("/teachers/{teacher_id}", status_code=204)
def delete_teacher(teacher_id: uuid.UUID, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)], cascade: Annotated[bool, Query()] = False) -> None:
    delete_simple_teacher(db, tenant, school_id, teacher_id, cascade)


@router.post("/teachers/{teacher_id}/deduplicate-assignments")
def deduplicate_assignments(teacher_id: uuid.UUID, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(deduplicate_teacher_assignments(db, tenant, school_id, teacher_id))


@router.post("/teachers/merge")
def merge_teachers(payload: TeacherMergeInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(merge_simple_teachers(db, tenant, school_id, payload))


@router.put("/ordering/teachers")
def teacher_order(payload: OrderedIdsInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_teacher_order(db, tenant, school_id, payload))


@router.post("/teachers/bulk", status_code=201)
def create_teachers_bulk(payload: BulkTeachersInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(create_simple_teachers(db, tenant, school_id, payload))


@router.post("/teachers/bulk-file", status_code=201)
async def create_teachers_file(
    school_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
    workload_limit: Annotated[int, Form()] = 24,
    allow_similar: Annotated[bool, Form()] = False,
) -> Any:
    content = await file.read()
    filename = (file.filename or "").lower()
    if filename.endswith(".xlsx"):
        sheets = _parse_xlsx(content)
    elif filename.endswith((".csv", ".txt")):
        sheets = _parse_csv(content)
    else:
        raise HTTPException(status_code=415, detail={"code": "teacher_file_must_be_xlsx_or_csv"})
    aliases = {normalize_text(value) for value in ("اسم المعلم", "المعلم", "الاسم", "teacher", "teacher name", "name")}
    names: list[str] = []
    for _, headers, rows in sheets:
        if not headers:
            continue
        matched = next((header for header in headers if normalize_text(header) in aliases), None)
        column = matched or headers[0]
        if matched is None and column.strip():
            names.append(column)
        for _, values in rows:
            cell = values.get(column, "")
            if not isinstance(cell, dict):
                names.append(str(cell).strip())
    if not any(name.strip() for name in names):
        raise HTTPException(status_code=422, detail={"code": "teacher_file_has_no_names"})
    return jsonable_encoder(create_simple_teachers(db, tenant, school_id, BulkTeachersInput(names=names, workload_limit=workload_limit, allow_similar=allow_similar)))


@router.post("/subjects", status_code=201)
def create_subject(payload: SimpleSubjectInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(create_simple_subject(db, tenant, school_id, payload))


@router.put("/subjects/{subject_id}")
def update_subject(subject_id: uuid.UUID, payload: SimpleSubjectInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(update_simple_subject(db, tenant, school_id, subject_id, payload))


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: uuid.UUID, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> None:
    delete_simple_subject(db, tenant, school_id, subject_id)


@router.put("/ordering/subjects")
def subject_order(payload: OrderedIdsInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_subject_order(db, tenant, school_id, payload))


@router.put("/sections/{section_id}")
def update_section(section_id: uuid.UUID, payload: SimpleSectionInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(update_simple_section(db, tenant, school_id, section_id, payload))


@router.delete("/sections/{section_id}", status_code=204)
def delete_section(section_id: uuid.UUID, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> None:
    delete_simple_section(db, tenant, school_id, section_id)


@router.put("/ordering/sections")
def section_order(payload: OrderedIdsInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_section_order(db, tenant, school_id, payload))


@router.put("/curriculum")
def curriculum(payload: CurriculumPlanInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_curriculum_plan(db, tenant, school_id, payload))


@router.post("/teachers/availability/copy")
def availability_copy(payload: AvailabilityCopyInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(copy_availability(db, tenant, school_id, payload))


@router.post("/assignments", status_code=201)
def assignment(payload: QuickAssignmentInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(quick_assignment(db, tenant, school_id, payload))


@router.put("/assignments/{assignment_id}")
def assignment_update(assignment_id: uuid.UUID, payload: QuickAssignmentInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(update_quick_assignment(db, tenant, school_id, assignment_id, payload))


@router.delete("/assignments/{assignment_id}", status_code=204)
def assignment_delete(assignment_id: uuid.UUID, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> None:
    remove_quick_assignment(db, tenant, school_id, assignment_id)


@router.post("/assignments/transfer")
def assignment_transfer(payload: AssignmentTransferInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(transfer_assignments(db, tenant, school_id, payload))


@router.post("/rules", status_code=201)
def preset_rule(payload: PresetRuleInput, school_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    return jsonable_encoder(save_preset_rule(db, tenant, school_id, payload))


@router.post("/generate")
def start_generation(payload: GenerateInput, school_id: uuid.UUID, background_tasks: BackgroundTasks, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> Any:
    result = generate(db, tenant, school_id, payload)
    if result.get("started") and result.get("run_id"):
        background_tasks.add_task(execute_solve_run, db.get_bind(), uuid.UUID(str(result["run_id"])))
    return jsonable_encoder(result)
