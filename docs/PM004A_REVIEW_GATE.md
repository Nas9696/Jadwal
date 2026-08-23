# PM-004A Review Gate — Advanced Rules, Quality and Explainability

Accept PM-004A when all of the following are true:

1. New scheduling rules are implemented through the typed SchedulingRule registry, not ad-hoc flags or React-only logic.
2. Hard rules are actually enforced by CP-SAT and soft rules contribute measurable weighted penalties.
3. Distribution rules work per project-global week/day and preserve combined sections, co-teaching, split assignments and shared teachers.
4. Consecutive/double/triple rules do not duplicate or lose lesson occurrences.
5. Assignment relationship rules validate scope and enforce same/not-same time/day/order correctly.
6. Fairness objectives are factual soft penalties and do not silently become hard constraints.
7. Optimization profiles are transparent server-side weight policies and affect fingerprint/objective when relevant.
8. Candidate and working timetable quality reports are based on persisted/current placements and contain traceable metrics.
9. Placement explanations come from structured solver/problem facts and do not invent reasons.
10. Alternative-slot explanations distinguish blocked alternatives from valid-but-worse alternatives and show penalty deltas where available.
11. Move-block explanations reuse PM-003C authoritative conflict facts rather than a divergent validator.
12. Infeasibility suggestions are derived from concrete blocking facts and never auto-relax hard rules.
13. Arabic RTL rule-builder/quality/explanation UX is usable without optimization jargon.
14. PostgreSQL migration/seed CI and every existing PM-001..PM-003C test remain green.
15. Legacy remains untouched.

Do not open a repair gate for cosmetic polish. Block progression only for rule correctness, solver semantics, false explanations, data integrity, or materially broken UX.
