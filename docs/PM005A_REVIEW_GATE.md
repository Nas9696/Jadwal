# PM-005A Review Gate — Waiting, Absence, and Substitution

Accept PM-005A only if all of the following are true:

1. Absences are expanded from the authoritative current WorkingTimetable without changing timetable placements.
2. Substitute eligibility uses project-global week/day + real half-open interval and checks shared teachers across all project schools.
3. Attendance mode never bypasses a real-time collision.
4. Active teacher and active school membership lifecycle rules are respected.
5. Teacher specialty is not a hard restriction by default; it is optional soft ranking only when policy enables it.
6. Teaching + waiting/substitution workload caps use explicit values and preserve legitimate zero settings.
7. Daily/weekly waiting limits and exemptions are enforced server-side.
8. Co-teaching absence semantics replace only the absent teacher position, not the whole lesson.
9. Ranked recommendations contain factual score components and deterministic tie-breaking.
10. Manual selection is allowed only for hard-eligible teachers; lower rank alone is not a blocker.
11. Assignment re-checks eligibility atomically at commit time and prevents double assignment/overlap.
12. Stale timetable/need state is surfaced explicitly; no silent remapping after timetable edits.
13. Cancel/unassign preserves history and updates coverage status correctly.
14. Tenant/school/project isolation is enforced for all reads/writes.
15. Arabic RTL daily UI makes uncovered needs obvious and supports absence → recommendation → assignment without browser dialogs.
16. Waiting/workload view shows base target, teaching load, assigned waiting/substitution, remaining capacity, exemptions, and limits.
17. PostgreSQL migration-from-empty + seed + integrity assertions and all prior tests remain green.
18. Legacy files remain untouched.

Review blockers only:
- collision/workload eligibility errors;
- data-integrity or concurrency errors;
- incorrect absence expansion;
- lifecycle/isolation violations;
- ranking facts inconsistent with actual eligibility/workload;
- materially broken daily workflow.

Do not open a repair gate for cosmetic polish, wording tweaks, or optional reporting enhancements.