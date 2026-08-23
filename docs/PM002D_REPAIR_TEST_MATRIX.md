# PM-002D Repair Test Matrix

Minimum regression coverage before acceptance:

- One multi-sheet XLSX job stages brand-new structure, teacher, subject, resource, curriculum, offering, and assignment; validate/preview performs zero authoritative writes; commit succeeds atomically.
- Staged duplicate/ambiguous references within the same job become conflicts, not guessed links.
- Same `group_key` + different subject is rejected.
- Same `group_key` + different weekly count is rejected.
- Same `group_key` + same scalar fields aggregates teachers/sections/resources and PM-002C preview matches committed coverage/workload.
- Existing subject/resource/teacher mutable differences are surfaced truthfully in safe mode; explicit update mode shows before/after for supported fields.
- Archived teacher/membership remains non-reactivated without explicit lifecycle action.
- PostgreSQL CI starts from an empty database, runs every Alembic migration through head, runs seed, then performs a basic integrity assertion.
- All prior Python/API/Scheduler and Web regressions remain green.
