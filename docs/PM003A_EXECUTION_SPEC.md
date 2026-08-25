# PM-003A Execution Spec — Timetable Project, Rule Framework, and Preflight

## Goal
Begin Phase 2 with the first real Smart Timetables workspace. A school administrator must be able to create a timetable project, choose its schools/terms, align multi-school cycles explicitly, express foundational hard/soft scheduling rules, and run a factual preflight that builds the exact typed scheduling problem that the CP-SAT solver will consume in PM-003B.

PM-003A does **not** generate a timetable yet. It creates the trustworthy boundary between authoritative school data and the solver.

## 1. Timetable project lifecycle
Create a real Arabic RTL workspace under `/timetables` (or an equivalent clear route) with:
- project list for the tenant;
- create project;
- edit project name/description/status while draft;
- project detail workspace;
- safe delete only when no dependent solver runs/versions exist;
- active school/complex scope display;
- created/updated timestamps.

A project may target:
- one school;
- multiple schools in one complex;
- an explicit school set.

Use the existing `TimetableProject` / `TimetableProjectSchool` direction rather than inventing a parallel model.

Each included school must have an explicit `term_id` belonging to that school.

## 2. Project school cycle alignment
The school calendar remains local. The solver calendar is project-global.

Add explicit cycle phase alignment per `TimetableProjectSchool`, e.g. `cycle_phase_offset` or an equivalent typed field.

Semantics must be documented and tested. Recommended definition:
- local cycle indexes are `0..L-1`;
- `cycle_phase_offset` is the local cycle week active on project-global week 0;
- a local week `i` occurs on project week `g` when `(g + cycle_phase_offset) % L == i`.

Defaults:
- cycle length 1 => offset 0;
- simple projects default offset 0;
- do not infer non-zero offsets silently from term dates.

Project global cycle length remains `LCM` of included school cycle lengths, bounded by the existing maximum (12 by default).

Update scheduler normalization contracts/tests so cross-school collision alignment uses the explicit project-school phase.

## 3. Authoritative scheduling problem builder
Create a service/domain boundary that builds a typed `SchedulingProblem` from database state for one project.

It must gather and validate:
- project schools and each selected term;
- active school shifts;
- local week patterns;
- schedulable lesson blocks only;
- normalized weekday indexes and real half-open intervals;
- project-global cycle expansion;
- active SectionOfferings in selected terms;
- active TeachingAssignments and relational teachers/sections/resources;
- canonical active teachers with active memberships;
- subjects/resources;
- curriculum demand facts when relevant to diagnostics;
- enabled project scheduling rules.

Do not let React assemble solver input.

Do not read legacy JSON assignment relationships.

The builder must be deterministic: same authoritative state + same project/rules => same ordered problem payload and stable IDs.

## 4. Lesson occurrence expansion
A `TeachingAssignment.weekly_occurrences` represents weekly demand for every applicable project-global week unless a future rule explicitly scopes otherwise.

Build deterministic lesson occurrence IDs such as:
`assignment-id@project-week-N#occurrence-M`
(or equivalent typed IDs).

Combined sections:
- one occurrence represents one lesson event serving all linked sections;
- do not duplicate the event per section.

Co-teaching:
- one occurrence carries all linked teachers;
- each teacher is reserved by the same event.

Resources:
- required relational resources travel with the event.

Split assignments remain separate events according to their own weekly occurrence count.

## 5. Candidate slot derivation
For each lesson occurrence derive candidate time slots from authoritative school calendar facts before CP-SAT.

At minimum candidate slots must respect:
- school;
- selected term/project scope;
- SectionOffering shift(s);
- local week pattern expanded into project-global week;
- enabled school days;
- schedulable lesson blocks only;
- actual start/end interval;
- hard foundational availability/placement rules implemented in PM-003A.

For combined sections with incompatible shifts/calendars, candidate slots are the intersection of valid simultaneous real-time slots. Empty intersection is a preflight error.

Attendance mode is descriptive/placement policy data, not a reason to ignore teacher time collision.

## 6. Generic SchedulingRule model
Add a project-scoped generic rule model instead of adding many booleans to teachers/subjects/classes.

Recommended fields:
- id;
- tenant_id;
- timetable_project_id;
- optional label/description;
- `rule_type`;
- `severity`: hard / soft;
- `weight` for soft rules;
- `selector` structured JSON;
- `parameters` structured JSON;
- enabled;
- timestamps.

JSON is acceptable for polymorphic selectors/parameters only if every rule type has a registered typed Pydantic schema and server-side reference validation.

A registry entry must define:
- type code;
- Arabic/English label;
- allowed severity;
- selector schema;
- parameter schema;
- reference validator;
- preflight effect;
- future solver translator seam;
- explanation metadata.

Unknown rule types or unsupported selector combinations must be rejected.

## 7. Foundational rule types in PM-003A
Implement real persistence, validation, builder effect, and UI for at least:

### Availability / forbidden time
- teacher unavailable — hard;
- section unavailable — hard;
- resource unavailable — hard;
- assignment forbidden time — hard.

### Preferred/avoided time
- teacher preferred time — soft;
- teacher avoided time — soft;
- assignment preferred time — soft;
- assignment avoided time — soft.

### Required placement
- assignment required time — hard, for one or more allowed exact project/local time selectors.

Selectors must support practical scopes such as school/week-pattern/day/period or real slot identifiers without relying on localized labels as identity.

Do not yet implement the full distribution/consecutive/fairness catalog; PM-003B will add solver-backed rules through the same registry.

## 8. Rule Builder UX
Inside project detail add a `العلاقات والقيود` tab/page.

The normal user should see friendly language, not optimization jargon.

Flow:
1. choose rule type;
2. choose target(s): teacher / section / resource / assignment as compatible;
3. choose time scope;
4. choose `إلزامي` (hard) or `تفضيل` (soft) where allowed;
5. for soft rules choose a friendly priority (low/normal/high/very high) mapped to documented numeric weights;
6. preview a plain-Arabic sentence;
7. save.

Support:
- list/search/filter rules;
- enable/disable;
- edit;
- duplicate;
- delete with in-app confirmation;
- clear validation messages.

No `prompt/alert/confirm` as the primary UX.

## 9. Preflight engine
Add a typed preflight endpoint/service for a project. It must build the same scheduling problem boundary used later by the solver and return structured diagnostics.

Each finding should include:
- severity: error/warning/info;
- code;
- Arabic-ready message;
- entity references;
- project week/day/time context where relevant;
- factual measurements (required/available/shortage);
- suggested remediation when safe, clearly marked as suggestion.

At minimum detect:
- no schools/terms selected;
- invalid/cross-school term references;
- non-contiguous local week patterns;
- project cycle over maximum;
- invalid phase offset;
- school/shift with no schedulable lesson slots;
- active assignment with no sections or teachers;
- inactive/invalid teacher membership reference;
- assignment section outside selected term;
- resource reference outside scope/inactive;
- lesson occurrence with zero candidate slots;
- section weekly demand > available schedulable slots;
- teacher weekly demand > candidate capacity;
- required resource demand structurally impossible where detectable;
- combined sections with no common time slots;
- contradictory hard required/forbidden time rules;
- duplicate equivalent hard rules (warning or validation conflict according to semantics).

Preflight is deterministic and makes zero scheduling-placement writes.

## 10. Readiness score/state
Project UI must show a real readiness summary derived from preflight:
- `غير مكتمل` when setup is missing;
- `توجد أخطاء تمنع التوليد` when blocking errors exist;
- `جاهز للتوليد` only when no blocking errors exist;
- warning count separately.

Do not fake a percentage unless it is computed from documented facts.

The future `Generate` button may appear disabled with `قريبًا — PM-003B`, but the readiness/preflight functionality must be real.

## 11. Typed API direction
Use `/api/v1` and tenant/project scoping.

Reasonable endpoints:
- project CRUD/list;
- project-school scope update;
- rules CRUD;
- rule registry/catalog;
- `POST /projects/{id}/preflight`;
- optional read-only problem summary endpoint for diagnostics/development (never expose excessive internal solver details to normal UI).

All cross-tenant/cross-school/cross-term references are rejected server-side.

## 12. Performance and determinism
A realistic school project should preflight quickly enough for interactive setup. Avoid N+1 queries across every occurrence where practical.

Use stable sorting for schools, weeks, slots, assignments, teachers, sections, resources, rules, and occurrences.

No random IDs inside an in-memory problem build when a deterministic derivation is possible.

## 13. Required tests
Preserve all PM-001 through PM-002D-R tests.

Add tests for at least:
- one-school project with one-week cycle;
- project term belongs to included school;
- multi-school project with shared teacher;
- cycle 1 vs 2 and explicit phase 0;
- cycle 1 vs 2 with non-zero phase;
- cycle 2 vs 3 global LCM 6 with phase alignment;
- invalid phase offset rejected;
- project cycle limit diagnostic;
- deterministic problem build;
- occurrence expansion per global week;
- combined sections create one event per occurrence, not duplicates;
- co-teaching occurrence reserves all teachers;
- split assignments remain independent;
- lesson blocks only, no break/prayer/activity as candidate lesson slots;
- real interval/weekday collision identity preserved;
- teacher unavailable removes candidate slots;
- required vs forbidden contradiction;
- combined sections no common slot => error;
- teacher demand > candidate capacity;
- section demand > capacity;
- cross-school/tenant rule references rejected;
- hard/soft rule schema validation;
- soft priority/weight persistence;
- Web project creation/scope/preflight/rule CRUD RTL flow.

## 14. Quality gates
Run:
- Python/API/Scheduler tests;
- Ruff;
- mypy;
- Web tests;
- ESLint;
- TypeScript;
- Next.js production build;
- PostgreSQL Alembic upgrade from empty;
- seed + integrity assertions in GitHub Actions.

## Out of scope
Do not implement in PM-003A:
- CP-SAT timetable generation;
- candidate solutions;
- timetable grid/editor;
- drag/drop/repair/locks;
- full distribution/consecutive/fairness rule catalog;
- natural-language AI rule creation;
- waiting/substitution;
- reporting/publishing.

## Acceptance
PM-003A is complete when a manager can create a timetable project, select one or multiple schools and the correct term for each, set cycle phase alignment, add foundational scheduling rules, run preflight, and receive factual blocking/warning diagnostics from the same deterministic typed problem builder that PM-003B will send into CP-SAT.

Required commit message:
`feat: build timetable project rule and preflight workspace`

Do not begin PM-003B until review.