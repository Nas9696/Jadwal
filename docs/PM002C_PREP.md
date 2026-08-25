# PM-002C Preparation Notes

PM-002B review repair is accepted. PM-002C may now proceed under `docs/PM002C_EXECUTION_SPEC.md` and `docs/PM002C_REVIEW_GATE.md`.

## Assignment relationship direction
- Teacher assignment membership remains relational through `TeachingAssignmentTeacher`.
- PM-002C must normalize section and resource assignment relationships into relational tables (or an equivalently integrity-safe model) rather than expanding reliance on `TeachingAssignment.section_ids` and `resource_ids` JSON arrays.
- Every assigned teacher must be an active member of the assignment's school.
- Every section offering, subject, and resource used by an assignment must belong to the same tenant/school, and assignment/section offering must share the same term.
- Specialty is descriptive only and never an eligibility restriction.
- Weekly assignment demand must be compared with authoritative `CurriculumRequirement` without silently changing curriculum demand.
- Teaching assignments must be term-scoped.
- Sections used for scheduling must have an explicit term+shift profile/offering rather than relying on permanent Section identity alone.

## Review status
PM-002B / PM-002B-R accepted at commit `e1b77cef3358fc6c73c81da1d15d9affba8a7459`.

Implementation authority for PM-002C is now:
- `docs/PM002C_EXECUTION_SPEC.md`
- `docs/PM002C_REVIEW_GATE.md`
- `docs/PM002C_UI_NOTES.md`