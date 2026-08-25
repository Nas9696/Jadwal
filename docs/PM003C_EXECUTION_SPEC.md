# PM-003C Execution Spec — Professional Timetable Editor

## Goal
Turn a generated PM-003B candidate into a professionally editable timetable without losing solver correctness. This phase delivers drag/drop editing, move analysis, swaps, locks, undo/redo, version snapshots, and minimal-change repair around user edits.

The priority is usable editing of a real generated timetable. Do not delay this phase for reporting, AI, waiting/substitution, or advanced future rules.

## 1. Editable timetable version
- Introduce an authoritative editable timetable/version derived from a persisted `TimetableCandidate`.
- Copy candidate entries into an editable relational version; never mutate the immutable solve candidate in place.
- Keep project/tenant scope, source candidate, version number, status, created_by placeholder if auth is not yet complete, timestamps, and change summary.
- Allow one version to be marked working/current for a project, with historical versions retained.

## 2. Full timetable views
Inside `/timetables` provide views for:
- general school/project timetable;
- class/section;
- teacher;
- subject;
- room/resource;
- project-global week tabs.

All views must render the same authoritative editable entries.

## 3. Drag/drop and move analysis
Before committing a move, call a server-side analysis endpoint. The browser must not invent conflict logic.

For an occurrence moved from slot A to slot B return typed facts:
- direct move valid/invalid;
- teacher conflicts;
- section conflicts;
- exclusive resource conflicts;
- hard-rule violations;
- lock violations;
- affected entries;
- score/soft-penalty delta where available;
- possible direct swap candidates;
- nearby alternative slots.

Use real project-global week + weekday + half-open interval semantics.

## 4. Apply move/swap
- A valid direct move is persisted atomically.
- Swap is atomic: both placements change or neither changes.
- Revalidate on commit; never trust stale client analysis.
- Preserve combined sections/co-teaching/split semantics.
- Resource exclusivity and attendance-mode semantics remain unchanged.

## 5. Locks
Support typed locks at least for:
- lesson/occurrence;
- teacher;
- section;
- day;
- period/time range;
- stage (if readily resolvable from section hierarchy);
- project-global week/region.

A lock may prevent movement or generation/repair depending scope. Store locks relationally or with typed selectors behind validation; do not accept arbitrary unchecked JSON.

UI must allow lock/unlock with clear Arabic labels.

## 6. Undo/redo and audit trail
Every persisted editing operation creates a change record with before/after placements and operation type.

Support:
- undo last applicable operation;
- redo after undo until a new divergent edit occurs;
- audit list with timestamp and factual summary.

Do not implement browser-only undo state.

## 7. Minimal-change repair
Add a CP-SAT repair operation using the existing scheduler package.

Input:
- current editable timetable;
- requested change or conflict context;
- locks;
- current foundational hard/soft rules.

Objective hierarchy:
1. hard constraints;
2. locks;
3. requested edit/repair target;
4. minimize number of moved occurrences;
5. minimize displacement/time distance;
6. minimize normal soft penalties.

Return a typed ChangeSet before apply:
- moved occurrence;
- from slot;
- to slot;
- reason/factual conflict resolved;
- total moved count;
- penalty change.

User must explicitly approve a repair ChangeSet before persistence.

## 8. Local repair UX
When drag/drop is invalid, show:
- why it is invalid;
- direct swap options;
- alternative slots;
- `إصلاح تلقائي بأقل تغييرات` action.

Do not regenerate the whole timetable silently.

## 9. Version snapshots
Allow user to create a named snapshot from current editable version and later:
- compare current vs snapshot;
- see changed occurrences count;
- restore snapshot as a new version (do not destructively rewrite history).

## 10. Concurrency/stale edits
Every mutation must carry a version/revision token. Reject stale edits with a structured `timetable_version_conflict` and require reload/reanalysis.

## 11. API direction
Use project-scoped endpoints such as:
- POST `/api/v1/timetable-projects/{project_id}/working-timetable/from-candidate/{candidate_id}`
- GET `/api/v1/timetable-projects/{project_id}/working-timetable`
- POST `/.../moves/analyze`
- POST `/.../moves/apply`
- POST `/.../swaps/apply`
- POST `/.../repair/preview`
- POST `/.../repair/apply`
- CRUD `/.../locks`
- POST `/.../undo`
- POST `/.../redo`
- snapshot/list/restore endpoints.

Exact paths may vary if contracts remain coherent.

## 12. Tests
Preserve all previous tests and add small deterministic fixtures for:
- create working timetable from immutable candidate;
- candidate remains unchanged after edits;
- valid direct move;
- teacher/section/exclusive-resource conflict analysis;
- shared teacher cross-school conflict;
- attendance mode does not bypass conflicts;
- combined/co-teaching move correctness;
- atomic swap;
- lock blocks move;
- unlock permits move;
- stale revision rejected;
- undo/redo persisted across reload;
- repair changes the minimum number of occurrences in a fixture;
- repair respects locks;
- repair preview does not mutate;
- repair apply exactly matches approved ChangeSet or rejects stale state;
- snapshot/compare/restore;
- Web drag/drop or equivalent interaction, conflict panel, locks, undo/redo and repair preview.

## 13. Performance
Move analysis should be fast for one occurrence and should not run a full long solve unless user requests repair. Repair defaults to a modest bounded time limit and small local neighborhood where possible.

## 14. Out of scope
Do not implement in PM-003C:
- PDF/Excel/image publishing;
- AI natural-language rule creation;
- waiting/substitution;
- teacher self-service;
- full explanation engine beyond factual move/repair reasons.

## Acceptance
PM-003C is accepted when a user can open a generated candidate, make safe drag/drop edits, understand conflicts, swap or request minimal-change repair, lock parts of the timetable, undo/redo changes, and retain version history without mutating the original candidate.

Required commit:
`feat: build professional timetable editor and repair`
