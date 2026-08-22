# Project Cycle Invariants

These invariants are mandatory for multi-school timetable projects.

## Local calendar vs project calendar
A school's `WeekPattern.cycle_week_index` is **local to that school**. It tells which local pattern applies inside that school's own repeating cycle.

A solver `TimeSlot` must additionally have a **project-global** cycle-week identity.

## Normalized cycle
For a timetable project containing schools with local cycle lengths `L1..Ln`:

`project_cycle_length = lcm(L1, L2, ..., Ln)`

Each local school week pattern is expanded into all project cycle weeks where it applies.

Example:
- School A cycle length 1: local A applies in project weeks 0 and 1 of a 2-week normalized project.
- School B cycle length 2: local A applies in project week 0, local B in project week 1.

Thus School A's single pattern can collide with either School B pattern depending on the project-global week.

## Collision identity
Two slots temporally overlap iff all are true:
1. same `project_cycle_week_index`
2. same normalized weekday index
3. `max(start_a, start_b) < min(end_a, end_b)`

The following must NOT determine temporal overlap:
- period number
- local week-pattern index
- school ID
- localized day label
- attendance mode
- slot ID

## Solver slot fields
A normalized solver slot should contain at minimum:
- `id`
- `school_id`
- `week_pattern_id` (local traceability)
- `local_cycle_week_index` or equivalent traceability
- `project_cycle_week_index`
- normalized `weekday_index`
- `starts_at_minute`
- `ends_at_minute`
- display `period`
- `attendance_mode`

## Safety bound
Normalization must be bounded. A configurable maximum project cycle length must be enforced (default recommendation: 12 weeks). If LCM exceeds the bound, preflight must reject the configuration with a clear diagnostic and suggested remediation.

## Determinism
Given the same school calendars and project scope, project-cycle expansion must be deterministic and independently unit-testable.