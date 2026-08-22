# Professional Manager — Codex Operating Constitution

## Product identity
The target product is **المدير المحترف | Professional Manager**. The first production module is **الجداول الذكية | Smart Timetables** for Saudi and Arabic-speaking schools.

This repository already contains legacy/static timetable utilities. Do not delete or rewrite legacy files unless a task explicitly requires migration. New production work belongs under `professional-manager/` unless a task says otherwise.

## Non-negotiable product principles
1. Arabic is the primary language and RTL is the primary layout. English is a switchable secondary language.
2. The product must support kindergarten, primary, intermediate, secondary, and multi-stage school complexes.
3. A single account may manage multiple schools/complexes, academic years, terms, shifts, and week patterns (A/B/C).
4. Days, periods, breaks, attendance/remote patterns, and period times are configurable by the school.
5. Teacher assignment is flexible. Never assume a teacher may teach only their formal specialty.
6. The scheduling engine must distinguish **hard constraints** from **soft preferences**. Hard constraints are never silently violated.
7. Every generated solution must return feasibility, score, violations, explanations, and useful alternatives.
8. Timetable editing must support drag/drop, conflict detection, swap, repair, minimal-change optimization, undo/redo, locks, group locks, and partial regeneration.
9. Locks may target a lesson, teacher, teacher group, class, subject, room, day, period range, or timetable region.
10. The system must support rooms/labs/resources, combined classes, split groups, and multi-teacher lessons as optional capabilities.
11. Waiting/substitution duty is workload-aware and configurable, including exemptions.
12. Daily absence handling must suggest substitutes fairly and explain why each substitute is ranked.
13. Import/export must support Excel/CSV and structured imports from officially available Noor/Madrasati exports. Never build unauthorized scraping or bypass controls.
14. Official Noor/Madrasati APIs may be integrated only when documented, authorized, and available to the deployment.
15. The product must keep historical versions and audit who changed what and when.
16. No feature is considered complete without validation, tests, error states, loading states, empty states, accessibility, and RTL review.
17. Prefer configurable rule engines over hard-coded school-specific behavior.
18. Never reduce an existing capability just to make a new feature easier to implement.

## Architecture rules
- New system root: `professional-manager/`.
- Web: TypeScript, React/Next.js, RTL-first.
- API: Python FastAPI, Pydantic v2, SQLAlchemy 2, Alembic.
- Database: PostgreSQL.
- Scheduler: independent Python package/service using Google OR-Tools CP-SAT behind an internal interface so another solver can be added later.
- Long solver jobs: asynchronous job model; do not block the request thread.
- Desktop: later Tauri shell over the web application and API contracts; do not fork business logic for desktop.
- Contracts must be versioned and typed.
- Tenant isolation is mandatory from the first schema.

## Scheduling engine contract
Every solve/repair operation must support:
- hard constraints
- weighted soft constraints
- deterministic seed option
- time limit
- multiple candidate solutions
- score breakdown
- unsatisfied preference report
- infeasibility diagnostics where possible
- full lock and partial lock
- repair existing timetable
- minimize changed assignments
- explain a placed lesson
- suggest alternatives for a requested move

Do not implement a naive greedy-only generator as the production engine.

## Rule/relationship engine
Use a generic rule model capable of targeting combinations of:
- teachers / teacher groups
- classes / grades / stages
- subjects
- rooms/resources
- days / week patterns
- periods / period ranges
- lesson assignments

Rule effects include at minimum:
- forbid
- require
- prefer
- avoid
- lock
- free/unavailable
- consecutive
- non-consecutive
- min/max per day
- min/max consecutive
- spread
- same-time
- not-same-time
- same-day
- different-day
- resource capacity/exclusivity
- fairness objective

Rules must be data-driven and extensible.

## UX rules
- A school manager must be able to complete common operations without knowing optimization terminology.
- Use Arabic educational vocabulary in the UI; solver terminology belongs in advanced/explanation views.
- Advanced capability must not make the default workflow complex.
- Always show the consequence of a destructive or large schedule change before applying it.
- Conflict messages must include cause + affected entities + at least one actionable resolution when possible.

## Quality gate for every task
Before claiming completion:
1. Read this file and the relevant files under `docs/`.
2. Preserve tenant isolation and permissions.
3. Add/update automated tests.
4. Run lint/type checks/tests relevant to changed code.
5. Verify Arabic RTL behavior for UI changes.
6. Document schema/API changes.
7. Report changed files, tests run, known limitations, and next recommended step.

## Decision policy
Codex may make routine technical choices consistent with these documents. It must not invent or silently change product policy, educational rules, security policy, or integration behavior. When a material product decision is genuinely undefined, surface options rather than encoding an arbitrary assumption.

## Source-of-truth documents
Read these before substantial implementation:
- `docs/PRODUCT_VISION.md`
- `docs/PRODUCT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MODEL.md`
- `docs/SCHEDULING_ENGINE.md`
- `docs/CONSTRAINT_CATALOG.md`
- `docs/ROADMAP.md`
