# PM-002C Review Gate

PM-002C must not be considered complete merely because an assignment grid renders or CRUD endpoints exist.

Review must verify these invariants from persisted data:

1. Assignments are scoped to an explicit school term.
2. Active sections for a term have an explicit shift through a relational section-offering/profile model.
3. Section and resource assignment relationships are relational and validated; JSON ID arrays are not authoritative.
4. Teacher assignment requires an active canonical teacher and active membership in the assignment school.
5. Specialty never blocks assignment.
6. Curriculum coverage is computed per section offering + subject from persisted assignments and compared against `CurriculumRequirement` without modifying curriculum demand.
7. Combined sections contribute the assignment count to each linked section but do not multiply teacher workload.
8. Co-teaching contributes the assignment count to every linked teacher.
9. Split assignments for the same section+subject are allowed and sum correctly.
10. Cross-school/tenant/term references are rejected by the server.
11. Subject/resource/teacher membership dependency protections use relational assignment data.
12. The bulk UI is genuinely efficient: matrix, cell editor, safe same-subject bulk actions, and advanced list for combined/co-teaching assignments.
13. All prior regression tests remain green.

Do not begin PM-002D until this gate is reviewed and accepted.