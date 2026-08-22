# Scheduling Engine — Professional Manager

## Purpose
The scheduler is a domain engine, not a UI helper. It receives a validated scheduling problem and returns one or more candidate solutions plus diagnostics/explanations.

## Solver strategy
Primary solver: Google OR-Tools CP-SAT.

The engine API must be solver-agnostic enough to allow future experimentation (hybrid heuristics, local search, decomposition) without changing product contracts.

## Input model
At minimum:
- normalized time slots including school, local pattern traceability, project-global cycle-week index, normalized weekday index, real half-open time interval, and display-only period number
- teachers and availability
- sections/groups
- subjects
- teaching assignments and occurrence counts
- rooms/resources
- hard rules
- soft rules with weights
- existing timetable for repair
- locks
- optimization profile
- time limit / solution count / seed

## Core decision
Assign each lesson occurrence to an allowed time slot and required resource set, subject to constraints.

School cycles are normalized before solving. The project cycle length is the LCM of included school cycle lengths, bounded to 12 weeks by default. Local slots repeat into every applicable project-global week. Cross-school teacher overlap is determined only by the same `project_cycle_week_index`, the same `weekday_index` (0..6), and intersecting real-time intervals (`max(start) < min(end)`). Local cycle indexes, localized day labels, slot IDs, school period numbers, and attendance mode do not define overlap.

## Mandatory hard constraints
- teacher cannot be in two incompatible lessons simultaneously
- section/group cannot be in two incompatible lessons simultaneously
- exclusive room/resource cannot be double-booked
- unavailable teacher/class/resource/time is respected
- required lock is preserved
- required simultaneous/group relations are honored
- occurrence count is exact unless a deliberately partial diagnostic solve is requested
- shift/week/day/period scope is valid

## Soft objectives
Weighted and configurable, including:
- minimize teacher gaps
- minimize student gaps where applicable
- spread subject across days
- avoid excessive consecutive lessons
- prefer/avoid periods for teacher/subject/class
- fairness of first/last/post-break periods
- minimize room changes
- honor preferred double/single lesson distribution
- reduce undesirable day concentration
- balance teaching and waiting duties
- minimize changes during repair

## Optimization profiles
Expose presets while still allowing advanced weight tuning:
- Balanced
- Teacher comfort
- Student learning rhythm
- Minimal changes
- Administration priorities
- Custom

## Multiple solutions
Return several materially different candidates, not duplicates with tiny score differences. Candidate metadata includes objective score, normalized quality, penalties, hard status, and diversity hints.

## Preflight
Before solve, detect obvious structural infeasibility such as:
- total required occurrences exceed capacity
- teacher demand exceeds available slots
- class demand exceeds available slots
- resource demand impossible under availability
- contradictory hard rules
- locked collisions

Preflight findings are actionable and localized.

## Infeasibility diagnostics
When no solution exists, do not return only `failed`.
Return:
- conflicting/likely blocking hard rules where diagnosable
- affected teachers/classes/resources
- capacity shortages
- suggested relaxations clearly marked as suggestions, never applied automatically

## Repair
Repair takes an existing timetable plus a requested change/event. Objective hierarchy:
1. preserve hard constraints
2. honor locks
3. satisfy requested change
4. minimize number of moved entries
5. minimize weighted disruption distance
6. optimize normal soft objectives

Return a ChangeSet with every move and reason.

## Move analysis
For drag/drop, API must support a fast analysis operation:
- valid direct move?
- conflicts
- direct swap candidates
- alternative target slots
- localized repair options
- estimated change count and score impact

## Explanation
Explanation is structured:
- placement facts
- constraints that ruled out alternatives
- soft objectives that favored this slot
- score impact
- alternative slots and why worse/invalid

Natural-language Arabic/English explanation is generated from these facts. Never invent solver reasons that are absent from structured evidence.

## Testing
Include deterministic fixtures for:
- simple feasible school
- impossible teacher collision
- room conflict
- teacher unavailability
- multi-stage shared teacher
- A/B week patterns
- consecutive lesson constraints
- partial locks
- repair with minimal changes
- multiple candidate diversity
- soft preference trade-offs
