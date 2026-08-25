# Domain Model — الجداول الذكية

## Organization hierarchy
- Tenant / Organization
- School Complex (optional)
- School
- Academic Year
- Term
- Shift
- Week Pattern (A/B/C...)
- Stage (KG/Primary/Intermediate/Secondary/custom)
- Grade
- Section/Class

## Time model
- School Day
- Week Pattern with a zero-based cycle-week index local to its school (A/B/C...). A project's global cycle is derived by bounded LCM normalization before solving.
- Period Template owned by a school and one of that school's week patterns, with real start/end time
- Period Instance
- Break / prayer / activity block
- Attendance mode: onsite / remote / hybrid

## People
### User
Authentication identity and permissions.

### Teacher
Tenant-scoped canonical educator identity. A teacher is linked to one or more schools through Teacher School Membership, which holds school-local metadata such as employee code, home-school status and active status. The same identity is reused across schools so the scheduler can detect shared-teacher collisions. Subject eligibility is not a hard restriction.

### Teacher School Membership
Relational teacher ↔ school association within one tenant. A teacher must never be duplicated merely because they teach in multiple schools.

### Teacher Group
Reusable set for rules, meetings, departments or custom grouping.

## Curriculum and teaching
### Subject
Reusable subject identity.

### Curriculum Requirement
Expected weekly load by stage/grade/section and optional defaults.

### Teaching Assignment
Central unit representing who teaches what to whom:
- one or more teachers
- one or more sections/groups
- subject
- weekly occurrence count
- allowed distribution patterns
- optional required resources/room
- optional simultaneous/subgroup semantics

### Lesson Occurrence
One scheduled occurrence of a teaching assignment.

## Resources
- Room
- Lab
- Field
- Device/resource pool
- Capacity/exclusivity properties

## Rules
### Rule
Generic relationship/constraint record.
Fields should include:
- tenant/school scope
- name/description
- enabled
- severity: hard or soft
- weight for soft rules
- rule type
- target selectors
- time selectors
- parameters JSON validated by type-specific schema
- source: manual/template/import/system

### Rule selector
Targets can reference explicit IDs and/or reusable groups for teachers, subjects, sections, stages, resources, days, periods, week patterns and assignments.

## Timetable lifecycle
### Timetable Project
Workspace with a relational school scope. It may cover one school, a complex, or an explicit set of schools. All included schools belong to the same tenant; complex-scoped projects include only schools in that complex. Each project-school relationship selects the term belonging to that specific school; there is no ambiguous project-wide term for multi-school projects.

### Solver Run
Immutable record of one solve attempt, settings, seed, limits and diagnostics.

### Candidate Solution
One generated option with score and breakdown.

### Timetable Version
Approved or editable snapshot derived from candidate/manual changes.

### Timetable Entry
Placement of a lesson occurrence into week/day/period plus resources.

### Lock
Explicitly protects entry/entity/range during generation or repair.

### Change Set
Structured list of moves/swaps/add/remove produced by manual editing or repair.

## Waiting and substitution
### Waiting Policy / Teacher Waiting Profile
Project-scoped policy defining the combined teaching-plus-waiting cap, daily and weekly waiting limits, fairness weights, optional specialty/same-school preferences, and exemption behavior. A teacher profile can explicitly override nullable limits or mark that canonical teacher exempt; zero is a valid limit and is never treated as missing.

### Teacher Absence
An immutable dated full-day or real-time interval anchored to a project-global cycle week, normalized weekday, current Working Timetable id/revision, school, and canonical teacher. A stale revision is surfaced and still-unassigned needs are rebuilt only by an explicit refresh.

### Substitution Need
One teacher replacement position for one affected Working Timetable occurrence. It snapshots the absent teacher, school, subject, project-global week/day, real half-open interval, source revision, coverage status, and optimistic version. A co-taught lesson therefore creates a need only for each teacher actually absent.

### Substitution Assignment
The authoritative active/cancelled relation between a need and a canonical substitute teacher. It retains recommendation rank, score breakdown, eligibility facts, manual-override marker, actor placeholder, and timestamps. The active relation is unique per need; assignment rechecks the current timetable, cross-school real-time collisions, absences, existing substitutions, hard unavailability, exemptions, and workload caps atomically.

## Imports
- Import Job
- Import Mapping
- Import Row/Error
- Provider Adapter metadata

## Audit
Every privileged mutation and timetable edit should emit an Audit Event with actor, tenant, school, entity, before/after metadata where appropriate, timestamp and correlation id.
