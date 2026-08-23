# PM-005A Execution Spec — Waiting, Absence, and Substitution

## Goal
Complete Phase 5 in one focused implementation: model waiting-duty capacity and policy, record daily teacher absences, rank valid substitutes from the authoritative timetable, assign replacements with fairness and workload controls, and expose a usable Arabic RTL daily workflow.

Do not expand this phase into publishing, notifications, Noor/Madrasati integration, or unrelated HR attendance.

## 1. Core principles
- The approved/current WorkingTimetable is the authoritative source of who is teaching, free, locked, and where.
- Waiting/substitution never alters the academic timetable itself.
- Teacher specialty remains descriptive by default and is never a hard eligibility restriction unless an explicit future policy enables it.
- A substitute must be truly free in the real half-open time interval and project-global week/day; attendance mode does not bypass a collision.
- Cross-school shared teachers must be checked across the whole timetable project.
- All tenant/school/term/project scope checks are server-side.

## 2. Workload and waiting policy
Add explicit typed policy/settings, preferably project- or school-scoped with safe defaults.

Required concepts:
- contractual/base workload target per teacher (reuse existing teacher/membership fields where authoritative);
- current teaching workload from TeachingAssignments / timetable occurrences;
- waiting-duty target/capacity;
- combined teaching + waiting maximum;
- optional per-day waiting maximum;
- optional per-week waiting maximum;
- exemption from waiting;
- unavailable days/periods and hard scheduling rules remain respected;
- optional policy weights for fairness and specialty preference.

Example that must work:
- base target = 24;
- teaching = 14;
- policy permits combined teaching + waiting up to 24;
- maximum theoretical waiting capacity = 10, subject to availability and exemptions.

Do not use truthiness fallbacks that turn legitimate zero values into defaults.

## 3. Persistent models
Add relational domain models such as:

### WaitingPolicy
- tenant_id
- school_id or timetable_project_id scope
- combined_workload_limit mode/value
- daily_waiting_limit
- weekly_waiting_limit
- fairness weights
- specialty preference enabled/weight
- enabled
- timestamps

### TeacherWaitingProfile / exception
Only if needed beyond existing teacher/membership fields:
- teacher/member scope
- exempt flag
- custom limits
- notes

### TeacherAbsence
- tenant_id
- timetable_project_id
- school_id
- teacher_id
- absence date/local school date
- project-global week index resolved explicitly
- weekday index
- optional full-day versus selected periods/time ranges
- reason/category text/code
- status open/covered/partially_covered/cancelled
- created/updated timestamps

### SubstitutionNeed
One row per affected timetable occurrence:
- absence_id
- working_timetable_entry_id / occurrence_id
- school
- week/day/start/end
- subject/sections/resources snapshot references as needed
- status unassigned/assigned/uncovered/cancelled

### SubstitutionAssignment
- need_id
- substitute_teacher_id
- source/recommendation metadata
- score/rank snapshot
- reason facts JSON typed schema or normalized companion rows
- assigned_at / cancelled_at
- audit actor placeholder

Avoid opaque blobs as the authoritative assignment relation.

## 4. Absence expansion
When an absence is created:
- resolve against the current WorkingTimetable;
- find all entries for the absent teacher matching the selected date/day/time range;
- create deterministic substitution needs for those occurrences;
- combined/co-teaching semantics:
  - if one teacher in a co-taught occurrence is absent, only that teacher position needs substitution;
  - the lesson itself remains scheduled;
  - if multiple teachers are absent, create separate teacher replacement needs or a typed multi-position representation that preserves count;
- absence creation must not mutate timetable placements.

If the working timetable revision changes later, do not silently remap an already-created absence. Surface stale/changed-entry facts and allow explicit refresh/rebuild of still-unassigned needs.

## 5. Candidate eligibility
A teacher is eligible for a need only if all hard checks pass:
- same tenant and valid active school membership relevant to the project;
- teacher is active and membership active;
- not absent during the target interval;
- no timetable entry overlapping the real target interval anywhere in the project, including another school;
- no already-assigned substitution/waiting duty overlap;
- no teacher-unavailable hard rule or applicable lock/policy prohibition;
- waiting exemption respected when policy says substitute selection is drawn from waiting pool;
- combined teaching + waiting/substitution workload does not exceed hard policy cap;
- daily/weekly waiting caps not exceeded.

Do not hard-filter by specialty by default.

## 6. Recommendation ranking
Return an ordered list with factual score breakdown. Suggested ranking components:
1. currently free and eligible — mandatory gate;
2. explicit waiting duty / remaining waiting capacity;
3. lower current combined workload;
4. fewer substitutions already assigned that day/week;
5. fairness debt/credit over the configured window;
6. subject specialty match only as an optional soft preference when policy enables it;
7. same school before cross-school only if policy enables and there is no collision;
8. deterministic stable tie-breaker.

Each candidate response must include explanation facts, e.g.:
- free at this time;
- teaching workload 14;
- waiting/substitution assigned 3;
- combined 17 / limit 24;
- 2 prior substitutions this week;
- specialty match: yes/no/not considered;
- rank components and total score.

Never return a made-up natural-language reason detached from these facts.

## 7. Assignment and concurrency
Assigning a substitute must:
- re-check eligibility at commit time;
- be atomic;
- reject stale need or stale timetable revision where material;
- prevent double assignment of the same need;
- prevent overlapping substitution assignments for the same substitute;
- update absence coverage status transactionally.

Use revision/version or optimistic concurrency on the daily workflow where appropriate.

Unassign/cancel must preserve audit history.

## 8. Optional manual override
Allow the manager to choose an eligible teacher outside the top-ranked recommendation list.
If the teacher is hard-ineligible, block and explain why.
If merely lower-ranked, allow assignment and record it as manual override with the same factual eligibility snapshot.

## 9. Daily operations UI
Add a dedicated Arabic RTL workspace, e.g. `/substitutions` or a clear tab under timetable operations.

Workflow:
1. choose project/school/date;
2. record absent teacher and full-day/selected periods;
3. show affected lessons/needs;
4. for each need show ranked substitutes;
5. assign one click with confirmation inside the app UI;
6. show uncovered needs prominently;
7. support unassign/cancel;
8. summary cards: absent teachers, needs, covered, uncovered, teachers carrying substitutions;
9. teacher/day view of waiting and substitutions.

No browser `alert/prompt/confirm`.

## 10. Waiting-duty planning view
Provide a practical view showing per teacher:
- contractual/base target;
- teaching load;
- assigned waiting/substitution count;
- remaining capacity;
- exemptions/custom limits;
- daily/weekly fairness.

If explicit pre-planned waiting slots are implemented, they must use actual timetable free intervals and never create collisions. If not necessary for this phase, a computed waiting capacity/pool plus actual substitution history is sufficient; do not invent a second timetable engine.

## 11. APIs
Typed versioned endpoints should cover:
- get/update waiting policy;
- workload/waiting summary;
- create/read/cancel absence;
- list absence needs;
- refresh unassigned needs when timetable changed;
- rank substitute candidates for a need;
- assign substitute;
- unassign/cancel substitution;
- daily summary/history.

Server returns display labels so Web does not reverse-engineer IDs.

## 12. Tests
Preserve all previous tests and add at least:
- base 24 / teaching 14 => remaining capacity 10 when policy permits;
- zero custom limits preserved;
- exempt teacher not recommended when waiting policy excludes them;
- full-day absence expands to exactly affected lessons;
- partial-period absence expands only matching entries;
- co-teaching one absent teacher creates one replacement position;
- shared teacher cross-school overlap makes substitute ineligible;
- attendance_mode remote does not remove overlap;
- teacher already teaching cannot substitute;
- teacher already substituting in overlapping interval cannot substitute again;
- daily/weekly/combined workload caps enforced;
- specialty is soft only and can be disabled;
- ranking favors fairer/lower-load eligible teacher deterministically;
- recommendation explanation score sums correctly;
- manual lower-ranked eligible override allowed;
- hard-ineligible override rejected with facts;
- atomic double-assignment prevention;
- concurrent/stale assignment rejection;
- cancellation/unassign updates coverage but preserves history;
- timetable revision change surfaces stale needs and explicit refresh behavior;
- tenant/school/project isolation;
- Web absence → recommendations → assign → uncovered/covered flow;
- Web waiting workload summary and exemptions.

Use small deterministic fixtures.

## 13. CI and migration
Maintain PostgreSQL 16 CI and run:
- Alembic from empty database through new head;
- seed;
- integrity assertions for new Phase 5 tables;
- Ruff;
- mypy;
- Python/API/Scheduler tests;
- Web tests;
- ESLint;
- TypeScript;
- Next.js production build.

## 14. Out of scope
Do not implement in PM-005A:
- PDF/Excel/image publishing;
- WhatsApp/email/push notifications;
- Noor/Madrasati APIs;
- payroll/HR attendance;
- desktop Tauri packaging;
- unrelated Professional Manager modules.

## Acceptance
PM-005A is accepted when a manager can record an absence against a real working timetable, receive deterministic factual ranked substitutes respecting real-time collisions and workload/waiting policy, assign/unassign atomically, see coverage and fairness, and all prior CI gates remain green.

Required commit:
`feat: add waiting absence and substitution workflows`

Do not start publishing/integration work until review.