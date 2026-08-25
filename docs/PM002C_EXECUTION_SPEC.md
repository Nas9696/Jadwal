# PM-002C Execution Spec — Teaching Assignment Matrix

## Goal
Build the professional bulk teaching-assignment workspace that connects the school master data created in PM-002A/PM-002B to the future timetable solver. This is the authoritative layer for answering: **which teacher(s) teach which subject to which section(s), how many times per week, in which term, and with which required resources?**

The experience should learn from the speed of mature timetable products without cloning their interface. Arabic RTL is primary, and the normal workflow must be understandable to a school timetable officer or principal without database terminology.

## Scope boundaries
PM-002C includes:
- term-scoped section activation / section offering,
- a bulk assignment matrix,
- relational teacher/section/resource assignment integrity,
- workload and curriculum-demand coverage calculations,
- multi-teacher and multi-section teaching groups,
- server-side validation, migrations, seed, API, UI, and tests.

PM-002C does **not** include:
- Excel/CSV import (PM-002D),
- automatic timetable generation / CP-SAT solving,
- teacher availability/preferences,
- generic rule builder,
- lesson distribution patterns such as `2+2+1+1`,
- waiting/substitution,
- Noor/Madrasati integrations.

## 1. Term scope is mandatory
Teaching assignments must not float globally across all years and terms.

Every authoritative assignment must belong to:
- tenant,
- school,
- term.

The selected term must belong to an academic year in the selected school and tenant. The assignment UI must expose an explicit academic-year / term selector and restore a clear current/default selection without silently mixing terms.

Assignments from different terms must never be summed together in the section coverage grid.

## 2. Section offering / shift scope
A permanent `Section` identity is not enough for scheduling because a section may be active in different terms or shifts over time.

Introduce an integrity-safe relational concept such as `SectionOffering` / `SectionTermProfile` with at least:
- tenant_id,
- school_id,
- term_id,
- section_id,
- shift_id,
- is_active,
- optional display/order metadata only if needed.

Invariant:
- at most one active offering for the same school + term + section unless a later explicit split-session feature requires otherwise,
- section, term and shift must all belong to the same tenant/school,
- a teaching assignment references section offerings for the same term as the assignment.

### UI
Within `/assignments`, provide a friendly setup state for the selected term:
- show available sections grouped by stage/grade,
- activate/deactivate sections for the term,
- assign each active section to a school shift,
- support bulk setting a shift for selected sections,
- if exactly one active shift exists, offer a one-click default but do not silently guess when multiple shifts exist.

Do not force the user to understand the term `SectionOffering`; visible Arabic can say «شُعب الفصل الدراسي» or equivalent.

## 3. Normalize TeachingAssignment relationships
The existing `TeachingAssignment.section_ids` and `resource_ids` JSON arrays must no longer be the authoritative relationship model for PM-002C.

Keep `TeachingAssignmentTeacher` relational and add integrity-safe relational tables, for example:
- `TeachingAssignmentSection` referencing a section offering,
- `TeachingAssignmentResource` referencing a school resource.

The final authoritative assignment model must represent:
- tenant_id,
- school_id,
- term_id,
- subject_id,
- weekly_occurrences > 0,
- zero or more optional notes/settings that are genuinely useful,
- one or more section offerings,
- one or more teachers,
- zero or more resources.

### Migration
Backfill any valid existing dev/seed JSON relationships into the new relational tables where practical. The new API/service/UI must read and write the relational model, not continue duplicating authority between JSON and relational storage. Deprecated JSON fields may be removed in the new migration or retained temporarily only if clearly non-authoritative and tested against drift.

## 4. Relationship rules
For every assignment:
- subject must belong to the same tenant/school and be active for new assignments,
- every section offering must belong to the same tenant/school/term,
- every teacher must be a canonical active teacher with an **active membership in the assignment school**,
- every resource must belong to the same tenant/school and be active for new assignments,
- specialty is descriptive only and never blocks assignment,
- duplicate relation rows are rejected,
- cross-tenant and cross-school IDs are rejected server-side.

Assignments may intentionally contain:
- multiple teachers (co-teaching),
- multiple sections (combined class/group teaching),
- multiple resources when needed.

The model must also allow the same section+subject demand to be split across multiple assignments/teachers. Therefore do **not** impose a simplistic unique `section + subject` assignment constraint.

## 5. Curriculum demand coverage
`CurriculumRequirement` remains the authoritative baseline weekly demand by grade + subject.

For a selected term and section offering:
- required weekly count = matching grade+subject curriculum requirement,
- assigned weekly count = sum of `weekly_occurrences` from all assignments in the selected term whose subject matches and whose assignment includes that section offering.

Each matrix cell must expose a status:
- missing: assigned = 0 while required > 0,
- partial: 0 < assigned < required,
- complete: assigned = required,
- over-assigned: assigned > required,
- no requirement: no authoritative curriculum requirement exists.

Never silently mutate `CurriculumRequirement` when editing assignments.

A combined assignment with two sections counts its weekly occurrences toward **each linked section's** demand. A co-taught assignment with two teachers counts the same weekly occurrences toward **each linked teacher's workload**.

## 6. Teacher workload semantics
For the selected school/term, calculate assigned teaching workload from persisted relational assignments.

For each teacher expose at least:
- contractual/base workload,
- teaching workload limit,
- assigned workload in the current school/term,
- a cross-school workload indicator for overlapping terms when the teacher is shared, if it can be computed reliably from term date ranges.

`teaching_workload_limit` is a planning warning in PM-002C, not an absolute eligibility rule unless a later explicit rule says otherwise. Do not silently reject an educationally valid assignment only because it exceeds that value. Instead return/display a clear overload warning and keep the data factual.

Never count section multiplicity twice for a combined lesson: an assignment of 5 weekly occurrences to two combined sections still contributes 5 to each teacher on that assignment, not 10.

## 7. Bulk assignment matrix UX
Create `/assignments` as a professional Arabic RTL workspace.

### Primary grid
Default view:
- rows: active section offerings, grouped/filterable by stage and grade,
- columns: subjects,
- cells: coverage and teacher assignment summary.

Each cell should make it easy to see:
- required weekly lessons,
- assigned weekly lessons,
- assigned teacher(s),
- status (missing/partial/complete/over),
- resource indicator when relevant.

Use sticky headers/first column and horizontal scrolling responsibly for large schools. Provide search/filter for stage, grade, shift, section and subject.

### Cell editor
Clicking a cell opens a drawer/dialog that can:
- create a new assignment for that section+subject,
- edit existing assignment groups contributing to the cell,
- choose one or more active teachers,
- set weekly occurrences,
- choose resources,
- optionally add additional sections for a combined lesson,
- optionally add additional teachers for co-teaching,
- remove an assignment with in-app confirmation.

The editor must show curriculum required vs assigned before/after save and teacher workload impact/warnings.

### Bulk actions
Support safe bulk actions, including at least:
- select multiple section cells for the **same subject** and assign a teacher,
- set/fill weekly occurrences from curriculum requirement for selected cells,
- bulk change teacher for selected compatible assignment rows,
- bulk clear/remove only with explicit confirmation and a preview/count.

Do not implement a magical auto-assign algorithm in PM-002C.

## 8. Assignment list / advanced view
In addition to the matrix, provide an advanced list/table view of teaching groups so combined sections and co-teaching are not hidden by the matrix abstraction.

Each row should show:
- subject,
- section(s),
- teacher(s),
- weekly occurrences,
- resource(s),
- selected term,
- warnings/status.

This is the authoritative place to inspect complex assignments.

## 9. Server-side diagnostics and validation
Mutation endpoints must return structured, user-mappable errors/warnings for at least:
- term not in school,
- section offering not in term/school,
- teacher not active / membership not active in school,
- subject not in school or inactive,
- resource not in school or inactive,
- weekly occurrences invalid,
- duplicate relation row,
- dependency conflict on deletion,
- curriculum over-assignment warning,
- teacher workload-limit warning.

Warnings must not be fabricated by the UI. The service should compute authoritative coverage/workload facts.

## 10. Deletion/deactivation semantics
- A section offering with teaching assignments cannot be silently deleted/deactivated; require assignments to be resolved first or provide an explicit safe workflow.
- Unlinking/deactivating a teacher membership remains blocked while active assignments in that school reference the teacher.
- Subject/resource dependency protection from PM-002B must now use relational assignment tables rather than JSON scanning.
- Deleting an assignment removes its join rows atomically.

## 11. API design
Use typed Pydantic schemas and service-layer validation.

Expose school-scoped, term-aware operations sufficient for:
- assignment workspace snapshot,
- section-offering CRUD/bulk activation,
- assignment create/update/delete,
- bulk assignment mutations,
- workload/coverage diagnostics.

Avoid one generic untyped endpoint that hides all business rules in arbitrary dictionaries.

## 12. Accessibility and Arabic UX
- Arabic RTL default,
- responsive matrix and dialogs,
- keyboard-usable cell/editor flow,
- accessible labels and focus management,
- loading/empty/error/success states,
- no primary `prompt/alert/confirm` flows,
- friendly Arabic terms rather than database terminology,
- English switch remains functional as scaffold.

## 13. Required tests
Preserve all PM-001 through PM-002B-R tests.

Add API/service tests for at least:
- assignment is term-scoped and rejects wrong-school term,
- section offering validates school/term/shift relationships,
- section offering uniqueness per term+section,
- teacher must have active membership in assignment school,
- shared teacher may be assigned in each school where membership is active,
- specialty mismatch does not block assignment,
- cross-school subject/section/resource is rejected,
- multi-teacher assignment persists relationally,
- multi-section combined assignment persists relationally,
- split section+subject across multiple assignments is allowed and coverage sums correctly,
- combined sections count coverage correctly per section,
- co-teachers count workload correctly per teacher,
- combined sections do not multiply teacher workload,
- over-assignment and workload-limit warnings are factual and returned,
- assignment delete removes join rows,
- subject/resource/membership dependency checks use relational assignments,
- inactive teacher/subject/resource cannot be newly assigned.

Add Web tests for at least:
- term selector and term isolation,
- section shift activation workflow,
- matrix renders rows/subjects/coverage states,
- cell editor teacher/resource selection,
- create/edit/delete assignment,
- teacher overload warning display,
- curriculum over/under/complete visual states,
- multi-select same-subject bulk assign flow,
- advanced assignment list displays combined/co-teaching assignments,
- in-app destructive confirmation.

## 14. Quality gates
Before completion run:
- Python/API/Scheduler tests,
- Ruff,
- mypy,
- Web tests,
- ESLint,
- TypeScript type-check,
- Next.js production build,
- Alembic upgrade from an empty database through all migrations,
- seed on a clean database with foreign keys enabled.

No Legacy files may be changed.

## Acceptance criteria
PM-002C is complete when a timetable officer can choose a school and term, activate sections into shifts, see a subject-by-section demand matrix, assign teachers and weekly counts quickly, create combined-section or co-teaching groups when needed, attach resources, and reload with the exact same relational data. Coverage and workload calculations must be authoritative, tenant/school/term relationships must be validated server-side, and no section/resource authority may rely on JSON ID arrays.

## Commit
Use:
`feat: build bulk teaching assignment matrix`

Do not start PM-002D until review.