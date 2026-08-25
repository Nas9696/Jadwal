# PM-001 Architecture Review Notes

Status: required corrections before PM-002.

## 1. Shared teachers must be first-class
The current `Teacher.school_id` model ties one teacher record to one school. Product requirements explicitly require shared teachers across primary/intermediate/secondary schools and school complexes.

Required direction:
- Make the canonical teacher tenant-scoped, not owned by exactly one school.
- Add a school membership/association table for teacher ↔ school with optional metadata such as home school, active flag, local employee code if needed.
- Teaching assignments continue to identify the school/context in which the teacher teaches.
- Do not duplicate the same human teacher merely because they teach in two schools.

Acceptance test: one teacher can belong to two schools in the same tenant and can have assignments in both without duplicate identity.

## 2. Timetable projects must support multi-school scope
The current `TimetableProject.school_id` restricts a project to one school. A school complex may require one solver run across several schools because teachers/resources may be shared.

Required direction:
- A timetable project must support scope = one school, one complex, or an explicit set of schools.
- Model this relationally; do not store authoritative school IDs only in an opaque JSON array.
- Solver input for a project must include all schools in its scope.

Acceptance test: one project can include two schools and identify shared-teacher conflicts across both.

## 3. Dashboard school scoping bug
`/api/v1/dashboard/{school_id}` currently counts Teacher/Subject/Section/Resource rows using tenant scope only, so a tenant with multiple schools can see aggregate counts while viewing one school.

Required direction:
- Dashboard counts for a selected school must be school-scoped.
- For entities without direct `school_id`, use correct joins or explicit scoped relationships.
- Add regression tests with at least two schools in the same tenant.

## 4. Tenant relationship integrity
Header-based tenant context is acceptable only as a PM-001 development scaffold and is not authentication.

Before production APIs expand:
- Service/repository write paths must verify that referenced IDs belong to the active tenant and permitted project scope.
- Add tests rejecting cross-tenant relationship creation.
- Keep authentication/RBAC as a separate planned capability; do not claim `X-Tenant-ID` is a security boundary by itself.

## 5. Required tests before PM-002
- Shared teacher across two schools.
- Multi-school timetable project.
- Dashboard counts remain school-specific inside one tenant.
- Cross-tenant relationship IDs are rejected.
- Existing PM-001 tests remain green.

Do not start the bulk editor or advanced school setup until these domain corrections are complete, because PM-002 will build directly on these models.
