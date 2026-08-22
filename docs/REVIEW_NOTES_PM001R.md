# Review Notes — PM-001R

PM-001R correctly fixed the canonical shared-teacher identity, relational teacher↔school membership, multi-school project scope, school-scoped dashboard counts, and tenant validation on the newly added write paths.

Before PM-002, one more foundational calendar/scheduler correction is required so multi-school conflict detection is mathematically correct.

## Findings

### 1. Scheduler TimeSlot lacks school and real-time interval
Current `TimeSlot` contains `week_pattern_id`, `day_code`, and `period`, but not the owning `school_id` nor `starts_at`/`ends_at` (or normalized minute boundaries).

This is insufficient for shared teachers across schools because two schools may have different period numbering and different bell times. A shared teacher collision must be defined by overlap of real time intervals within the same cycle week/day, not by matching slot IDs or period numbers.

### 2. Database PeriodTemplate is disconnected from WeekPattern
`PeriodTemplate` is school-scoped but has no `week_pattern_id`. Product requirements explicitly support A/B/C week patterns with different onsite/remote days and potentially different periods. The database must connect period/day configuration to the selected week pattern.

### 3. Multi-school TimetableProject has a single term_id
`Term` is school-scoped through `AcademicYear.school_id`, while `TimetableProject` can now include multiple schools. A single project-level `term_id` cannot faithfully represent a multi-school project where each school has its own term row. Move term selection to project-school scope or introduce an equivalent relational calendar-scope model.

## Required invariant
For any two assignments using the same canonical teacher, the solver must be able to determine whether their candidate placements overlap even when the assignments belong to different schools with different bell schedules.

## Recommended direction
- Give persisted period/day slots an explicit week-pattern association.
- Add explicit school identity and comparable temporal boundaries to scheduler slot contracts.
- Represent project calendar/term selection per school for multi-school projects.
- Add tests with two schools whose period numbers differ but clock times overlap, and the reverse (same period number but non-overlapping clock times).

Do not start feature-heavy PM-002 work until these invariants are fixed, because later rule and solver work will depend on them.
