# Calendar and Cross-School Scheduling Invariants

These invariants are mandatory for Smart Timetables.

1. A timetable project may span one or multiple schools.
2. Each school may have different bell times, period counts, breaks, shifts, week patterns, and attendance modes.
3. A shared canonical teacher may have assignments in multiple schools.
4. Teacher collision is based on overlapping real time intervals in the same cycle week/day, not on equal period numbers or equal slot IDs.
5. Resource and section collision are evaluated within their owning school unless a future shared resource is explicitly modeled.
6. Every persisted schedulable period belongs to a school and a week/calendar pattern.
7. A multi-school project resolves the academic term/calendar context for every included school separately.
8. Solver contracts must contain enough normalized temporal data to evaluate cross-school overlap deterministically without querying UI state.
9. Alternating local week patterns are expanded into a bounded project-global cycle using the LCM of school cycle lengths; collision never compares local indexes directly.
10. Remote/onsite is a placement attribute/policy and must not erase time collision for a teacher unless an explicit business rule permits simultaneous remote activity.
