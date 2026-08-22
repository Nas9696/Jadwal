# PM-002A — School Setup Workspace & Core Academic Structure

## Goal
Turn the Professional Manager foundation into the first genuinely usable school-configuration experience. A school manager should be able to open the web app, select a school, configure its academic calendar and school-day structure, and maintain stages/grades/sections through real API-backed screens.

This is the first visible product slice of Phase 1. It must be production-shaped, not a static mockup.

## Scope

### 1. App shell and navigation
Create an Arabic RTL administrative shell with:
- product name: **المدير المحترف**
- active school selector
- main navigation with at least: الرئيسية، إعداد المدرسة، الهيكل الدراسي، المعلمون، المواد والموارد، الإسناد، الجداول الذكية
- only implemented destinations should be fully interactive; future destinations may show a clear "قريبًا" state without fake data/actions
- responsive desktop-first layout that remains usable on tablet/mobile
- English switch remains supported by the existing i18n foundation

### 2. School setup overview
Create `/setup` (or equivalent) as a guided configuration hub with completion/status cards for:
- school identity
- academic year & terms
- shifts
- week patterns
- school days & timetable blocks
- stages/grades/sections

Show real persisted data and incomplete-state guidance.

### 3. Academic years and terms
Provide tenant- and school-scoped CRUD for:
- AcademicYear: name, starts_on, ends_on, active/current flag or equivalent policy
- Term: name_ar/name_en optional where useful, order, starts_on/ends_on if required by implementation

Rules:
- dates must be valid and terms must belong to the selected school's year
- cross-tenant and wrong-school references must be rejected server-side
- do not silently delete dependent records

### 4. Shifts
Add a first-class `SchoolShift` model, migration, CRUD, and UI.
Examples: صباحي، مسائي.
Fields should include at least school, code, Arabic name, optional English name, active flag, order.
The model must be ready for future timetable-project shift scoping without forcing all schools to use more than one shift.

### 5. Week patterns
Build API and UI around the corrected `WeekPattern` model.
The manager can configure one or more patterns such as A/B/C and their local `cycle_week_index`.
Requirements:
- contiguous zero-based cycle indexes per school
- duplicate code/index rejected
- default simple school may have one pattern A with index 0
- UI explains alternating weeks in plain Arabic

### 6. School days and timetable blocks
Do not encode weekdays only as arbitrary text.
Add a school-day configuration entity or equivalent persisted model containing at minimum:
- school_id
- shift_id
- week_pattern_id
- `weekday_index` 0..6
- enabled flag
- optional localized display label/override

Provide a visual day editor for the selected week pattern + shift.

Manage `PeriodTemplate` rows for each configured day with:
- block order
- block type: lesson / break / prayer / assembly / activity / custom non-teaching
- display period number nullable for non-lesson blocks
- Arabic label optional
- start/end time
- attendance mode: onsite / remote / hybrid
- schedulable boolean or a documented derivation from block type

Rules:
- intervals must be valid
- blocks in the same school/shift/week/day must not accidentally overlap unless a future explicit capability allows it
- lesson numbers are presentation/ordering metadata, never collision identity
- break/prayer/activity blocks must not be treated as ordinary lesson demand
- preserve the PM-001R3 local/project cycle invariants; do not store `project_cycle_week_index` in school configuration

### 7. Stages, grades, sections
Provide real CRUD and nested Arabic UX:
- stages: رياض أطفال، ابتدائي، متوسط، ثانوي, plus custom names
- grades under stage
- sections/classes under grade

Do not hard-code Saudi stage counts; allow templates/default helpers while keeping data editable.
Support flexible section names such as 1، أ، 1/أ، 101, etc.

### 8. API design
Use versioned `/api/v1` endpoints and service-layer validation.
Do not place business validation only in React.
All reads/writes are tenant scoped and selected-school scoped where applicable.
Return useful Arabic-ready error codes/messages or stable message keys where reasonable.

### 9. UX quality
Every implemented screen must include:
- loading state
- empty state
- validation errors
- save success feedback
- safe delete confirmation
- keyboard-accessible controls
- RTL layout review

The user should not need to understand database/solver vocabulary.

### 10. Tests
Add API/service tests for CRUD and cross-tenant/wrong-school safety.
Add tests for:
- invalid year/term dates
- non-contiguous or duplicate week pattern indexes
- day/block interval overlap rejection
- wrong week pattern / shift / school linkage rejection
- stage→grade→section ownership
- a simple school with one week pattern
- A/B/C configuration retained correctly

Add web component/integration tests for at least:
- school selector/setup navigation
- adding/editing a week pattern or day/block flow
- Arabic RTL shell

## Out of scope for PM-002A
- authentication/RBAC production completion
- teachers/subjects/resources CRUD (PM-002B)
- teaching-assignment bulk grid (PM-002C)
- Excel/CSV import mapping (PM-002D)
- CP-SAT solving
- rule builder
- drag/drop timetable editor

## Acceptance criteria
- A manager can configure a real school's academic year, terms, shifts, A/B/C patterns, enabled weekdays, lesson/break/prayer/activity blocks, stages, grades and sections entirely from the web UI and the data survives reload.
- API rejects cross-tenant and cross-school references.
- Period/day configuration preserves the calendar invariants established in PM-001R1/R2/R3.
- All existing tests remain green.
- New Python/API tests, web tests, Ruff, mypy, ESLint, TypeScript and Next production build pass.
- Alembic upgrade + seed on a clean database pass.
- Legacy files remain untouched.

## Commit
When complete, commit as:
`feat: build school setup and academic structure workspace`

Do not begin PM-002B until review.
