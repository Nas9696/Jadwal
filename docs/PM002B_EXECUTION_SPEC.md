# PM-002B Execution Spec — Teachers, Subjects, Curriculum Load, and Resources

## Goal
Build the second visible school-data workspace for **Professional Manager / Smart Timetables**. PM-002B turns the existing school setup into usable master-data management for teachers, subjects, curriculum weekly load, and physical resources. The result must be real persisted product behavior, not mock UI.

## Scope boundaries
PM-002B includes:
- teachers and teacher↔school memberships,
- teacher workload master data,
- subjects,
- curriculum weekly requirements by grade,
- rooms/labs/resources,
- professional Arabic RTL UI, API, validation, migrations, seed, and tests.

PM-002B does **not** include:
- teaching-assignment bulk grid (PM-002C),
- Excel/CSV import (PM-002D),
- solver implementation,
- generic rule builder,
- teacher availability/preferences constraints,
- waiting/substitution workflows,
- Noor/Madrasati integration.

## 1. Teacher identity and school memberships
`Teacher` remains a **tenant-scoped canonical identity**. Never create a second teacher record merely because the same person works in another school.

Required canonical fields:
- canonical code / stable internal identifier,
- Arabic name,
- optional English name if useful without breaking existing model,
- specialty reference (descriptive only),
- contractual/base workload target,
- teaching workload limit,
- active/archive state if introduced safely.

`specialty_reference` is never a hard eligibility restriction for subject assignment.

`TeacherSchoolMembership` is the school-specific relationship and must support:
- current school,
- local employee code,
- active/inactive membership,
- home-school flag,
- shared-teacher visibility.

### Home-school invariant
A canonical teacher may be linked to multiple schools in the same tenant, but at most one active membership may be marked `is_home_school=true`. Setting a new home school must clear the previous one server-side in one transaction. Protect the invariant at database/service level when practical.

### Teacher UI
Create a real `/teachers` workspace for the selected school:
- searchable/filterable teacher list,
- add a brand-new canonical teacher and membership,
- link an existing tenant teacher to the selected school without duplicating identity,
- edit canonical teacher data,
- edit current-school membership data,
- show a clear badge when the teacher is shared with another school,
- show the schools linked to the teacher where the signed-in tenant is allowed to see them,
- unlink/deactivate the teacher from the current school without deleting the canonical teacher when other memberships exist,
- destructive canonical deletion only when safe and with dependency protection.

Do not fake assigned workload before PM-002C. If teaching assignments exist in seed/tests, calculated assigned load may be shown; otherwise label it clearly as not yet assigned / zero from persisted assignments.

## 2. Subjects
Create school-scoped Subject management with at least:
- code,
- Arabic name,
- optional English name,
- active state if introduced,
- optional category/short label only if it serves a real UI purpose.

A subject belongs to the selected school for PM-002B. Subject codes/names should have sensible school-scoped uniqueness rules and clear conflict errors.

Create a professional `/subjects-resources` (or equivalent clearly named) workspace with tabs/sections for subjects, curriculum load, and resources.

## 3. Curriculum weekly requirements
Add a relational `CurriculumRequirement` (or equivalently well-named model) instead of hiding weekly lesson counts in UI state.

Minimum fields:
- tenant_id,
- school_id,
- grade_id,
- subject_id,
- weekly_occurrences / weekly lesson count > 0,
- optional notes or template-source metadata only if genuinely useful.

Invariant:
- unique requirement for a given school + grade + subject,
- grade and subject must belong to the same selected school and tenant,
- cross-school/cross-tenant IDs are rejected server-side.

UI must let the manager:
- select a grade,
- see subjects and weekly counts,
- add/edit/remove weekly requirements quickly,
- understand total weekly requested lessons for the grade,
- persist and restore after reload.

Do not implement detailed distribution rules (1+1+1, 2+2+1, etc.) here; those belong to assignment/constraint work. PM-002B only establishes authoritative weekly demand.

## 4. Rooms and resources
Extend the existing `Resource` model safely as needed and provide CRUD for at least:
- code or stable school-local identifier,
- Arabic name,
- resource type: classroom/room, science lab, computer lab, gym, library/learning-resources, field/playground, other,
- capacity optional,
- exclusive boolean,
- active state if useful.

Resource identity is school-scoped. Cross-school mutation is rejected.

The UI should make common school resources easy to create and distinguish visually without hard-coding only Saudi examples.

## 5. API/service design
Use explicit typed schemas and service-layer validation. Do not put material business invariants only in React.

At minimum expose school-scoped read/create/update/delete operations needed by the UI for:
- teacher memberships and canonical teacher editing,
- subjects,
- curriculum requirements,
- resources.

Tenant teacher discovery/search for linking an existing canonical teacher may be tenant-scoped, but the mutation that links the teacher to a school must validate both teacher and school belong to the active tenant.

Do not claim `X-Tenant-ID` is authentication; it remains development tenant context until auth/RBAC is implemented.

## 6. Deletion and dependency semantics
Avoid destructive cascades that silently remove scheduling data.

- Removing a teacher from one school should remove/deactivate only that membership unless canonical deletion is explicitly requested and safe.
- A teacher with another school membership must survive unlinking from the current school.
- A subject referenced by curriculum requirements or teaching assignments must not be silently deleted; return a clear dependency conflict or require dependent records to be removed first.
- A resource already referenced by future/current assignments must not be silently deleted.
- Curriculum requirements may be removed explicitly with confirmation.

## 7. UX requirements
Arabic RTL remains default. Keep the existing school selector and app shell.

Provide:
- loading states,
- empty states,
- search/filter where lists can grow,
- clear add/edit dialogs or drawers,
- in-app validation and server error feedback,
- in-app delete confirmation (no primary `alert/prompt/confirm` flows),
- responsive layout,
- accessible labels/focus behavior,
- success feedback.

The teacher screen must be understandable to a non-technical school manager. Avoid database terminology such as canonical/membership in visible Arabic copy; use friendly concepts such as «المعلم» و«مدارسه» و«المدرسة الأساسية».

## 8. Tests and regression coverage
Preserve all PM-001/R1/R2/R3 and PM-002A tests.

Add API/service tests for at least:
- one canonical teacher linked to two schools without duplication,
- teacher list for School A excludes teachers not linked to School A,
- linking cross-tenant teacher is rejected,
- duplicate school membership is rejected,
- changing home school clears previous home-school membership and invariant is protected,
- unlinking School A does not delete teacher still linked to School B,
- specialty reference never blocks teacher creation/linking or future subject eligibility,
- subject CRUD is school/tenant scoped,
- curriculum requirement rejects wrong-school grade or subject,
- duplicate grade+subject requirement is rejected,
- weekly count must be positive,
- resource CRUD and wrong-school mutation rejection,
- dependency-safe delete behavior where applicable.

Add Web tests for at least:
- teacher search/list and shared-school badge,
- link existing teacher flow versus create new teacher flow,
- teacher edit + membership edit,
- subjects/resources tabs or equivalent navigation,
- curriculum weekly count persistence/editing,
- delete confirmation inside application.

## 9. Quality gates
Before completion run:
- Python/API/Scheduler test suite,
- Ruff,
- mypy,
- Web tests,
- ESLint,
- TypeScript type-check,
- Next.js production build,
- Alembic upgrade from empty database through all migrations,
- seed on a clean database with foreign keys enforced.

No Legacy files may be changed.

## Acceptance criteria
PM-002B is complete when a school manager can select a school and, through the web UI, manage its teachers (including a genuinely shared teacher), subjects, grade-level weekly curriculum counts, and rooms/resources; all changes persist after reload; tenant/school relationship errors are rejected server-side; and the same teacher identity can be reused across schools without duplication.

## Commit
Use:
`feat: build teachers subjects curriculum and resources workspace`

Do not start PM-002C until review.