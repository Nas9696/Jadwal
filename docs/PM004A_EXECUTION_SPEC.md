# PM-004A Execution Spec — Advanced Rules, Quality and Explainability

## Goal
Move quickly from a technically valid timetable to a professionally useful school timetable. Complete the highest-value scheduling rules that real schools need, make their effects measurable, and add factual explanation APIs/UI for placements, alternatives, move blocks and candidate quality.

Do not delay this phase for AI natural-language commands, waiting/substitution, publishing or visual polish unrelated to rule correctness.

## 1. Preserve existing solver/editor invariants
PM-003B/PM-003C remain authoritative:
- CP-SAT is the production solver.
- collision identity is project-global week + normalized weekday + real half-open interval;
- attendance mode does not remove collision;
- combined sections are one occurrence carrying all sections;
- co-teaching is one occurrence carrying all teachers;
- split assignments remain independent;
- candidate snapshots remain immutable;
- working timetable edits/repair retain revision, locks, audit and zero-write previews.

## 2. Typed rule registry expansion
Continue using the generic `SchedulingRule` registry. Every new rule type must define:
- typed selector schema;
- typed parameter schema;
- allowed hard/soft severity;
- reference validation and school/tenant/project scope;
- preflight translation where structural checking is possible;
- CP-SAT translation;
- explanation metadata;
- tests.

Do not add ad-hoc boolean columns to core domain models for each rule.

## 3. High-value rule types required now
Implement at least the following professionally useful rules.

### Distribution / daily limits
- `assignment_max_per_day` — hard or soft.
- `assignment_min_days` / spread across at least N distinct days — hard or soft where meaningful.
- `teacher_max_lessons_per_day` — hard or soft.
- `section_max_lessons_per_day` — hard or soft.
- `teacher_max_consecutive_lessons` — hard or soft.
- `section_max_consecutive_lessons` — hard or soft.
- `assignment_avoid_same_day_repeat` — soft by default, hard allowed if schema permits.

### Consecutive / gap rules
- `assignment_require_consecutive_block` with block size 2 or 3; occurrences must be linked deterministically into blocks without duplicating lesson count.
- `assignment_forbid_consecutive`.
- `assignment_min_gap` in lesson blocks/time between occurrences on the same project-global week/day where applicable.

### Subject/time preferences
- `subject_preferred_time` — soft.
- `subject_avoided_time` — soft.
- optional hard subject forbidden/required time only if implemented without duplicating assignment rules.

### Assignment relationships
Support typed selectors for two or more assignments where appropriate:
- `assignments_same_time` — hard.
- `assignments_not_same_time` — hard.
- `assignments_same_day` — hard or soft.
- `assignments_different_day` — hard or soft.
- `assignment_before_assignment` — hard or soft.

Relationship rules must validate that assignment scopes can coexist in the selected project and must not silently create impossible cross-term references.

### Resource preferences
- `assignment_required_resource_type` — hard if the project has resource type metadata sufficient to validate it.
- `assignment_preferred_resource` — soft.
- `minimize_resource_changes` — soft for assignments/sections where resource choice is actually modeled. If current candidate slots do not yet permit dynamic resource choice, expose only rules that can be truthfully enforced and document the limitation instead of simulating support.

### Fairness objectives
Implement measurable soft objectives at least for:
- teacher gaps;
- teacher first-period count balance;
- teacher last-period count balance;
- excessive teaching streak penalty.

Use explicit weights/profile settings. Do not convert fairness preferences into hard rules unless the user explicitly creates a hard limit rule.

## 4. Optimization profiles
Add project-level presets that map to transparent weight configurations:
- Balanced / متوازن;
- Teacher comfort / راحة المعلمين;
- Student rhythm / إيقاع تعلم الطلاب;
- Administration priorities / أولويات الإدارة;
- Custom / مخصص.

A preset is a server-side weight/profile configuration, not hidden React logic. Persist the chosen profile/settings with the timetable project or solve request. Changing profile must change the solver input fingerprint when it affects optimization.

Do not claim that a preset is universally “best”; it is only a weight policy.

## 5. Quality report
For each generated candidate and current working timetable, expose a factual quality report containing at least:
- hard violations: must be zero for a valid timetable;
- total weighted soft penalty;
- penalty by rule ID/type/category;
- teacher gap totals and per-teacher outliers;
- first-period/last-period distribution summary;
- consecutive-streak summary;
- distribution-rule violations;
- resource-preference violations where supported;
- comparison against another candidate/version when requested.

Do not invent a percentage score unless a mathematically defined bounded normalization is implemented and documented. Default UI should use labels such as «جزاء أقل» / «أفضل في راحة المعلمين» with factual metrics.

## 6. Placement explanation service
Add a typed server-side explanation endpoint for a candidate entry or working timetable entry.

Example direction:
`GET /api/v1/timetable-projects/{project_id}/.../entries/{entry_id}/explanation`

Return structured facts such as:
- selected slot facts: school/week/day/start/end;
- hard constraints satisfied by the chosen placement;
- alternative candidate slots considered;
- for each sampled alternative: `valid`, blocking hard reasons, or soft penalty delta;
- soft rules that favored/penalized the chosen slot;
- relevant teacher/section/resource occupancy facts;
- concise Arabic explanation text generated from those structured facts, not from invented reasoning.

The explanation engine may use deterministic templates. An LLM is not required in PM-004A.

## 7. Why a move is blocked
Reuse PM-003C move analysis facts and improve their presentation:
- exact blocking teacher/section/resource/lock/rule;
- conflicting lesson label and time;
- whether direct swap is valid;
- nearest valid alternatives ranked by minimal change and soft penalty impact.

Do not duplicate a separate conflict engine for explanations; explanations must consume the same authoritative validation facts.

## 8. Why no solution / remediation
For preflight and solver infeasibility:
- preserve distinction between proven infeasible and unknown/time-limit;
- return factual structural shortages and contradictory hard rules when known;
- add suggested relaxations only when they are derived from a concrete blocking rule/capacity fact;
- never automatically relax a hard rule.

Example suggestions:
- increase teacher availability by one slot;
- reduce a hard max-per-day;
- disable one of two contradictory required/forbidden rules;
- change combined-section shift when no common slot exists.

## 9. Rule Builder UX
Expand the Arabic RTL rule builder so a timetable manager can create the new rules without seeing solver jargon.

Use category grouping:
- التوفر والأوقات؛
- توزيع الحصص؛
- الحصص المتتالية؛
- العلاقات بين الإسنادات؛
- الموارد؛
- الراحة والتوازن.

Each form should preview a sentence before save, for example:
- «بحد أقصى 4 حصص للأستاذ أحمد في اليوم.»
- «توزع رياضيات أول متوسط (أ) على 4 أيام على الأقل.»
- «تكون حصتا المختبر متتاليتين.»
- «يفضل عدم وجود فراغات في جدول الأستاذ أحمد.»

Retain edit/copy/enable-disable/delete from PM-003B/PM-003C.

## 10. Quality and explanation UX
Inside `/timetables` add concise panels/tabs:
- «جودة الجدول»;
- «لماذا هنا؟» for selected lesson;
- «لماذا لا يمكن النقل؟» from move analysis;
- candidate/version comparison.

Avoid dense technical language. Show exact affected entities and actionable facts.

## 11. Solver performance
Use compact CP-SAT formulations:
- daily grouping by project-global week/day;
- interval/order/group variables only when the corresponding rule exists;
- avoid all-pairs constructions when grouped cardinality constraints are sufficient.

Keep CI fixtures small and deterministic. Production solve time limits remain bounded.

## 12. Tests
Preserve all prior tests and add focused tests for:
- max lessons/day teacher and section;
- assignment max per day and min days;
- max consecutive teacher/section;
- required double/triple consecutive block;
- forbid consecutive;
- minimum gap;
- subject preferred/avoided time objective;
- same-time/not-same-time relationships;
- same-day/different-day relationships;
- ordering rule;
- fairness gap/first/last penalties;
- profile changes objective/fingerprint;
- combined/co-teaching behavior under daily/consecutive rules;
- shared teacher across schools under daily/consecutive rules;
- hard rule infeasible fixture with factual remediation;
- placement explanation chosen slot facts;
- blocked alternative explanation;
- valid-but-worse alternative with penalty delta;
- move-block explanation reuses PM-003C conflict data;
- quality report candidate vs working timetable;
- Web rule builder categories, quality panel and explanation panel.

## 13. Out of scope
Do not implement in PM-004A:
- LLM/natural-language rule creation;
- waiting/substitution;
- PDF/Excel/image publishing;
- notification workflow;
- Noor/Madrasati APIs;
- broad visual redesign unrelated to these features.

## Acceptance
PM-004A is accepted when a school can express the high-value distribution/consecutive/relationship/fairness constraints above, CP-SAT enforces/optimizes them correctly, the user can see a factual quality report and understand why a lesson is placed or blocked, and all PostgreSQL/Python/Web CI gates remain green.

Required commit:
`feat: add advanced scheduling rules and explainability`

Do not start PM-004B natural-language assistant until review.
