# PM-002B Review Notes

PM-002B is materially successful and CI is green, but review found a few teacher-lifecycle correctness issues that should be repaired before PM-002C builds teaching assignments on top of this master data.

## 1. Inactive school membership can become a dead-end

`teacher_snapshot()` returns only active memberships for the selected school. The `available_teachers` list is derived from those active memberships only. Therefore a teacher whose existing membership in this school is changed to `is_active=false` disappears from the school list and then appears as an available tenant teacher. Trying to link that teacher again attempts to insert a second `(tenant_id, teacher_id, school_id)` membership and conflicts with the uniqueness constraint.

Required invariant/behavior:
- Never create a duplicate teacher-school membership to reactivate a teacher.
- A previously inactive membership must be discoverable and reactivatable through a clear service/API/UI path.
- The user should be able to distinguish «غير نشط في هذه المدرسة» from «غير مرتبط بهذه المدرسة».
- Add regression coverage for deactivate → reload → reactivate.

## 2. Home-school display is incomplete for shared teachers

The teacher snapshot returns linked school objects but not the membership metadata for those linked schools. The UI therefore can mark «الأساسية» only when the *current school's* membership is home. If a shared teacher is viewed from School B while School A is the home school, no linked school is shown as the home school.

Required behavior:
- Return linked-school membership metadata (at least school id/name, `is_home_school`, `is_active`, and local employee code if appropriate).
- Display the actual home school regardless of which school is currently selected.
- Keep the existing at-most-one-active-home invariant.

## 3. Editing a workload value of zero changes the form default

The teacher edit form currently uses expressions equivalent to `base_workload || 18` and `teaching_workload_limit || 24`. Because zero is a valid persisted value, editing a teacher whose value is `0` displays `18`/`24` instead and can silently overwrite valid data.

Required behavior:
- Preserve persisted zero values exactly; use nullish/undefined fallback rather than truthiness fallback.
- Add a Web regression test that edits a teacher with zero workload values and verifies the form/payload remains zero unless the user changes it.

## 4. Canonical inactive state versus active school membership

Because `Teacher.is_active` is now an archive/active state, do not silently create or reactivate an active school membership for an inactive canonical teacher while leaving the canonical identity archived. Choose and document a consistent behavior: either prevent that operation with a clear message, or explicitly reactivate the canonical teacher as part of a deliberate user action. The UI must not present an archived teacher as normally active without explanation.

## Quality gate

Preserve all previous tests and run Python/API/Scheduler, Ruff, mypy, Web tests, ESLint, TypeScript, production build, Alembic from empty database, and seed with foreign keys.

Do not start PM-002C until this review repair is accepted.