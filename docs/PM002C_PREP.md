# PM-002C Preparation Notes

PM-002C will build the bulk teaching-assignment workspace. Before implementation, preserve these invariants from prior reviews and avoid leaning on weak JSON-only relationships for new assignment behavior.

## Assignment relationship direction
- Teacher assignment membership remains relational through `TeachingAssignmentTeacher`.
- PM-002C should normalize section and resource assignment relationships into relational tables (or an equivalently integrity-safe model) rather than expanding reliance on `TeachingAssignment.section_ids` and `resource_ids` JSON arrays.
- Every assigned teacher must be an active member of the assignment's school unless an explicitly documented cross-school project rule permits otherwise later.
- Every section, subject, and resource used by an assignment must belong to the same tenant and school as the assignment.
- Specialty is descriptive only and never an eligibility restriction.
- Weekly assignment demand must be compared with authoritative `CurriculumRequirement` without silently changing curriculum demand.

These are preparation notes only. Do not implement PM-002C until PM-002B review repair is accepted.