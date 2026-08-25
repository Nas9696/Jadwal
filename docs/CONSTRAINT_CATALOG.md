# Constraint Catalog — العلاقات والقيود

## Severity
Every rule is either:
- `hard`: must never be violated
- `soft`: may be violated at a measurable penalty

The UI may present friendlier Arabic labels, but storage and solver semantics remain explicit.

## Availability and placement
- teacher unavailable / preferred / avoided
- class unavailable / preferred / avoided
- subject preferred/avoided period
- room/resource unavailable
- assignment restricted to selected days/periods/week patterns
- require/forbid first or last period

## Distribution
- max/min lessons per day
- max/min consecutive lessons
- exact/allowed distribution pattern (e.g. 2+1+1+1)
- spread across N days
- avoid same subject repeated in one day
- require consecutive block
- forbid consecutive block
- minimum gap between occurrences

## Relationships
- two or more assignments same time
- two or more assignments not same time
- same day / different day
- one before another
- linked double/triple period
- teacher group common free period
- teacher group forbidden common busy period

## Resources
- exclusive room/resource
- capacity
- required room type
- preferred room
- minimize room changes
- resource setup buffer when configured

## Workload/fairness
- minimize teacher gaps
- cap teaching streak
- balance first periods
- balance last periods
- balance after-break periods
- balance waiting duties
- waiting exemptions
- target combined teaching + waiting workload

## Locks
- lesson lock
- teacher timetable lock
- teacher-group lock
- day lock
- period-range lock
- class lock
- stage lock
- timetable-region lock

## Complex teaching
Optional but first-class model support:
- multiple teachers in one lesson
- combined classes
- split class groups
- shared teachers across stages/schools in a complex

## Extensibility
Constraint implementation must be registered by type with:
- validated parameter schema
- selector compatibility
- solver translation
- explanation translator
- preflight validation when applicable
- automated tests

Do not add ad-hoc boolean columns to core entities for every new scheduling rule.
