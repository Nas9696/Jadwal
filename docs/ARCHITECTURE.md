# Architecture — Professional Manager

## Target structure
```text
professional-manager/
  apps/
    web/              # Next.js TypeScript RTL-first frontend
    api/              # FastAPI application
  packages/
    contracts/        # shared schemas/types generated or mirrored safely
    ui/               # reusable design system
  scheduler/          # independent Python scheduling engine
  infra/              # docker/dev/deploy manifests
  tests/              # cross-service integration/e2e
```

## Core technology
- Frontend: Next.js + TypeScript + React.
- API: FastAPI + Pydantic v2.
- Persistence: PostgreSQL + SQLAlchemy 2 + Alembic.
- Scheduling: Python + Google OR-Tools CP-SAT.
- Background jobs: abstraction for queue-backed solver jobs. Local development may start with an in-process adapter, but API contracts must model asynchronous runs from day one.
- Desktop: later Tauri wrapper using the same web/API contracts.

## Service boundaries
### Web
Presentation, forms, grid editors, drag/drop, localization, optimistic UX, printable views. No scheduling business logic in the browser beyond lightweight validation and conflict previews based on API contracts.

### API
Authentication/authorization, tenant context, school data, rule CRUD, import/export orchestration, schedule versioning, job orchestration, audit log.

### Scheduler
Pure domain input -> solver model -> candidate solutions, diagnostics and explanations. It must not know HTTP, UI, or tenant authentication.

## Tenancy
Every mutable domain record is scoped through organization/tenant and school where relevant. Cross-school complexes are represented explicitly; never rely on global ids without tenant checks.

## Versioning
A timetable is not overwritten in place. Use timetable projects/runs/versions so generation, repair and manual edits can be compared and rolled back.

## Explainability
Persist enough metadata to explain solver outcomes: active constraints, penalties, objective contribution, placement alternatives, and repair changes. Explanation generation must be based on structured facts, not fabricated prose.

## Integration boundary
No Noor/Madrasati credentials scraping. Define import adapters and an integration-provider interface. Official APIs, if available later, implement that interface.

## Security minimum
- RBAC + scoped permissions.
- audit events for privileged and timetable changes.
- server-side validation even when UI validates.
- secrets only via environment/secret manager.
- no sensitive data in logs.
- import files treated as untrusted input.

## Engineering principle
Build a modular monolith first (web + API + scheduler package boundaries) with clean interfaces. Split services only when scale or deployment requirements justify it.
