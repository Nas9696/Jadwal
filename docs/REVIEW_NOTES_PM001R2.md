# Review Notes — PM-001R2

PM-001R2 correctly moved cross-school collision detection from display period numbers to real time intervals and correctly scoped calendar periods to school + week pattern. It also moved term selection to each school inside a multi-school timetable project.

One foundational gap remains before PM-002: **local school cycle indexes are not yet a project-global time identity**.

Example:
- School A has a 1-week cycle: A only (`local index 0`) and repeats every week.
- School B has a 2-week cycle: A (`local index 0`) / B (`local index 1`).

On real project week 1, School A local A overlaps School B local A.
On real project week 2, School A local A also overlaps School B local B.

Therefore comparing only `cycle_week_index` from each school's WeekPattern is insufficient. A shared teacher can be double-booked in the second project week even though the two local indexes are 0 and 1.

The solver boundary must consume **expanded project-global cycle slots**, not compare local pattern indexes directly.

Required direction:
1. Keep each school's local WeekPattern and local cycle index for configuration.
2. Compute a timetable project's normalized cycle length as the least common multiple (LCM) of the included schools' cycle lengths.
3. Expand each school's local week patterns into every matching `project_cycle_week_index` across that normalized project cycle.
4. Collision uses: same `project_cycle_week_index` + same normalized weekday + overlapping half-open real-time interval.
5. Local `week_pattern_id` remains traceability metadata; it is not the global collision identity.
6. Use a normalized weekday integer (for example ISO-like 0..6) in solver contracts. Localized day labels belong to UI/configuration.
7. Put a safe upper bound on normalized project cycle length and reject/explain pathological configurations rather than creating an unbounded LCM expansion.

This must be corrected before PM-002 builds calendar CRUD and bulk configuration around the contract.