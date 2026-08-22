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
- Period Template
- Period Instance
- Break / prayer / activity block
- Attendance mode: onsite / remote / hybrid

## People
### User
Authentication identity and permissions.

### Teacher
School-scoped educator profile. Contains contractual workload limits, exemptions and preferences, but subject eligibility is not a hard restriction.

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
Workspace for a school/term/shift/week-pattern scope.

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
### Duty Policy
Defines workload target, exclusions, fairness and limits.

### Waiting Assignment
Teacher assigned to an available duty slot.

### Absence
Teacher absence window.

### Substitute Recommendation
Ranked candidate with score, reasons and conflicts.

## Imports
- Import Job
- Import Mapping
- Import Row/Error
- Provider Adapter metadata

## Audit
Every privileged mutation and timetable edit should emit an Audit Event with actor, tenant, school, entity, before/after metadata where appropriate, timestamp and correlation id.
