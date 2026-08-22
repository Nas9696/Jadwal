# Roadmap — Professional Manager / Smart Timetables

## Phase 0 — Foundation
- Establish product constitution and architecture.
- Create new `professional-manager/` workspace without breaking legacy timetable utilities.
- Add local Docker development, environment examples, lint/type/test commands, CI.
- Establish Arabic RTL design tokens and localization framework.

## Phase 1 — School data MVP
- Auth/tenant/school structure.
- Academic years, terms, shifts, week patterns.
- Stages, grades, sections.
- Teachers, subjects, curriculum requirements.
- Rooms/resources.
- Configurable days, periods, breaks and attendance modes.
- Teaching assignment CRUD and bulk grid.
- Excel/CSV import framework with preview and mapping.

## Phase 2 — Constraint engine + first solver
- Generic rule schema and rule builder.
- Preflight validation.
- CP-SAT model for collision-free placement.
- Availability, distribution, consecutive, resource and core preference rules.
- Generate multiple candidates.
- Score breakdown and diagnostics.

## Phase 3 — Professional timetable editor
- Full timetable views by school/stage/class/teacher/subject/resource.
- Drag/drop and swap analysis.
- Locks and group locks.
- Undo/redo and audit history.
- Repair with minimal changes.
- Version comparison and rollback.

## Phase 4 — Explainability and assistant
- Why was this lesson placed here?
- Why can't I move it?
- Suggested alternatives.
- Arabic natural-language rule commands with confirmation preview.
- Infeasibility remediation suggestions.

## Phase 5 — Waiting, absence and substitutions
- Waiting-duty policies and workload balancing.
- Exemptions and limits.
- Daily absence workflow.
- Ranked substitute recommendations with reasons.
- Daily print/export.

## Phase 6 — Reporting, publishing and integrations
- PDF/Excel/image print templates.
- A4/A3, color/monochrome, QR/logo/signature options.
- Teacher self-service preferences.
- Publish/notify workflow.
- Official Noor/Madrasati adapters when authorized APIs or stable official exports exist.

## Phase 7 — Platform expansion
- Desktop Tauri distribution.
- Supervisory multi-school dashboards.
- Additional Professional Manager modules: duty rosters, supervision, plans, meetings, tasks and related school operations.

## Definition of done for the first public beta
A real multi-stage school can import or enter its data, express hard and soft requirements, produce at least three valid candidate timetables, understand quality/violations, manually edit with conflict assistance, repair with minimal changes, print teacher/class/general schedules, and retain versions/audit history.
