# PM-003C Review Gate — Professional Timetable Editor

Accept PM-003C only if:

1. Generated solve candidates remain immutable; edits occur in a derived working timetable/version.
2. Move analysis and conflict detection are server-side and use project-global week + weekday + real half-open interval.
3. Teacher, section, exclusive-resource, hard-rule and lock violations are revalidated on commit.
4. Combined sections and co-teaching remain one occurrence carrying all linked entities; split assignments stay independent.
5. Direct move and swap are atomic.
6. Locks are typed/scoped and actually block incompatible move/repair operations.
7. Undo/redo is persisted, not browser-only.
8. Minimal-change repair uses CP-SAT or the production solver boundary and prioritizes locks plus fewest moved occurrences.
9. Repair preview performs zero schedule writes and apply revalidates against a revision token.
10. Stale concurrent edits are rejected with a structured conflict instead of silently overwriting.
11. Snapshots/history are durable and restoring creates a new version rather than rewriting history.
12. UI provides usable Arabic RTL views by general timetable, class, teacher and resource, with clear conflict/repair feedback.
13. PostgreSQL migration-from-empty + seed + all prior tests remain green; Legacy is untouched.

Do not create a repair gate for cosmetic polish. Block only correctness, data-integrity, stale-edit, collision, lock, undo/history, or repair-minimality failures.