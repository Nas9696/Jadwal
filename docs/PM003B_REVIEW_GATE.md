# PM-003B Review Gate — First CP-SAT Candidates

Accept PM-003B only if all of the following are true:

1. A PM-003A-ready project can start a persisted solve run without blocking the HTTP request for the full solve.
2. Google OR-Tools CP-SAT is the actual placement engine; no greedy/mock fallback is presented as production generation.
3. Every lesson occurrence is placed exactly once in a successful candidate.
4. Teacher, section, and exclusive-resource collisions are prevented using project-global week + weekday + real half-open interval, including cross-school shared teachers.
5. Combined sections, co-teaching, split assignments, attendance modes, and cycle phase behavior retain PM-003A semantics.
6. Existing hard time rules are enforced and existing soft preferred/avoided rules affect objective penalties without becoming hard constraints.
7. Candidate penalty breakdown is factual and traceable to rule IDs/types; no invented quality percentage.
8. Multiple requested candidates are actually distinct when alternatives exist.
9. Solve run/candidate/entry persistence reloads correctly and includes a deterministic input fingerprint.
10. Preflight errors block solve start; solver `infeasible` and `unknown/time_limit` are not conflated.
11. Candidate UI displays real persisted entries and labels, not a mock table.
12. PM-003A visual project-scope editing and rule edit/copy/toggle debt is completed in the same UI pass.
13. PostgreSQL migration-from-empty + seed + integrity CI remains green.
14. All PM-001 through PM-003A tests remain green and Legacy remains untouched.

Do not open a repair gate for cosmetic/polish findings. Block progression only for correctness, data-integrity, collision, solver, persistence, or materially broken UX issues.