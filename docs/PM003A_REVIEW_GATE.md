# PM-003A Review Gate

PM-003A begins the solver phase, so it must not be accepted merely because a project form and rule CRUD exist.

Review must verify:

1. `TimetableProject` scope is tenant-safe and each included school has an explicit term belonging to that school.
2. Multi-school cycle alignment has explicit, tested phase semantics; local week indexes are not mistaken for project-global weeks.
3. The authoritative problem builder is server/domain-side, deterministic, and reads relational assignment links only.
4. Lesson occurrences are expanded correctly per project-global week; combined sections do not duplicate teacher workload/events and co-teaching carries all teachers on one event.
5. Candidate lesson slots come only from enabled schedulable lesson blocks and respect SectionOffering shifts, normalized weekday, real time interval, local/global cycle mapping, and hard foundational time rules.
6. Attendance mode never disables real-time teacher collision logic.
7. SchedulingRule uses a typed registry: unknown types, invalid selectors, cross-tenant/cross-school targets, and invalid parameters are rejected server-side.
8. Hard and soft semantics are explicit; soft weights/priorities persist and are not silently converted to hard rules.
9. Rule Builder is Arabic-first RTL and understandable to a non-technical timetable manager.
10. Preflight uses the same problem builder boundary intended for PM-003B; it is not a separate approximate React-only calculation.
11. Preflight returns structured factual diagnostics with blocking errors versus warnings and no placement writes.
12. Capacity diagnostics correctly account for combined sections, co-teaching, split assignments, shared teachers, selected shifts, and project-global weeks.
13. Combined sections with no common real-time candidate slots are blocked.
14. Required/forbidden hard-time contradictions are detected.
15. A project is marked `جاهز للتوليد` only when no blocking preflight errors remain.
16. No CP-SAT timetable generation is smuggled into PM-003A; solver generation remains PM-003B.
17. PostgreSQL migration+seed CI remains green and all PM-001..PM-002D-R tests remain green.
18. Legacy files remain untouched.

Special review attention:
- phase offset formula and cycle 2/3 fixtures;
- term/school ownership at DB and service layers;
- deterministic stable IDs/order in the in-memory problem;
- no localized day name or period number used as collision identity;
- no breaks/prayer/activity becoming lesson candidates;
- teacher specialty remains descriptive only.