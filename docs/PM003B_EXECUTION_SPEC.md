# PM-003B Execution Spec — First Real CP-SAT Timetable Generation

## Goal
Produce the first real, persisted timetable candidates from a PM-003A project using Google OR-Tools CP-SAT. This phase is intentionally focused: generate valid collision-free schedules, honor the foundational hard rules and soft time preferences, return multiple materially different candidates, persist solve runs/candidates/entries, and show them in `/timetables`.

Do not delay this phase for advanced editor, repair, AI, waiting/substitution, or the full future constraint catalog.

## 1. Solver boundary
Use the PM-003A server-side problem builder as the authoritative input source. Move/extend contracts into the scheduler package where appropriate so the API does not maintain a second incompatible solver model.

Solver input must include enough metadata to enforce:
- occurrence IDs and assignment IDs;
- project-global week;
- candidate slots;
- teacher IDs;
- section IDs;
- resource IDs plus exclusivity;
- slots with school, project-global week, weekday and real half-open interval;
- enabled hard/soft rules;
- deterministic seed/time limit/solution count.

No React-side solver input construction.

## 2. CP-SAT decision model
For each lesson occurrence and candidate slot create a placement decision.

Hard constraints:
- every occurrence is placed exactly once;
- a teacher cannot occupy two lessons whose selected slots overlap in the same project-global week/day, including across different schools;
- a section cannot occupy two overlapping lessons;
- an exclusive resource cannot occupy two overlapping lessons;
- PM-003A hard unavailable/forbidden/required-time rules remain enforced;
- combined sections remain one occurrence carrying all sections;
- co-teaching remains one occurrence carrying all teachers;
- split assignments remain separate occurrences;
- attendance mode never removes a real-time collision.

Collision must use real half-open overlap, not period number or localized day labels.

## 3. Soft objective for first solver
Implement the existing PM-003A soft time rules only:
- teacher preferred time;
- teacher avoided time;
- assignment preferred time;
- assignment avoided time.

Weights are persisted rule weights. Return a structured penalty breakdown by rule ID/type and total weighted penalty.

Do not invent a fake 0–100 quality percentage in this phase. Lower penalty is better. Candidate rank and penalty breakdown are sufficient.

## 4. Multiple candidates
Default request: 3 candidates, configurable 1..5.

Candidates must be materially different. After each accepted solution, add a no-good/diversity constraint so a later candidate differs in at least a meaningful number of occurrence placements (minimum one, preferably configurable fraction for larger problems).

Use deterministic seed behavior so identical input + seed gives reproducible candidate ordering where CP-SAT permits.

Persist whether a candidate is `optimal` or `feasible`, objective/penalty, solve time, and diversity count versus best candidate.

## 5. Solve run persistence
Add relational models such as:
- `TimetableSolveRun`: tenant, project, input fingerprint, status queued/running/completed/infeasible/failed, requested candidates, time limit, seed, started/completed timestamps, solver status, diagnostics;
- `TimetableCandidate`: run, rank, solver status, total penalty, penalty breakdown, diversity metadata;
- `TimetableEntry`: candidate, occurrence ID, assignment ID, project-global week, slot ID, school ID, weekday, start/end, teacher/section/resource relational or safely typed persisted references sufficient for later editor/history.

Prefer relational authoritative schedule entries over one opaque candidate JSON blob.

A solve run is an immutable snapshot of the problem input. Compute a deterministic SHA-256 fingerprint of the canonical solver problem and store it.

## 6. Background solve API
Do not block the HTTP request for the whole solve.

Provide an execution seam appropriate for the current modular monolith, e.g. an in-process background executor/thread with persisted run status, while keeping the solver package independent so a real worker queue can replace it later.

API direction:
- POST `/api/v1/timetable-projects/{project_id}/solve` → create run, return run ID/status;
- GET `/api/v1/timetable-projects/{project_id}/solve-runs/{run_id}`;
- GET candidate details/entries;
- optional list runs for project.

Reject starting a solve when PM-003A preflight has blocking errors.

Prevent accidental duplicate concurrent active runs for the same project unless explicitly supported.

## 7. Infeasible/unknown behavior
If CP-SAT returns infeasible:
- persist run status `infeasible`;
- return the latest preflight diagnostics plus a solver diagnostic code;
- do not fabricate a specific reason that the solver did not prove.

If time limit is reached with a feasible solution, persist it as `feasible`.
If no feasible solution is found before the limit and status is unknown, return `unknown/time_limit` distinctly from proven infeasible.

## 8. Timetable candidate UX
Inside `/timetables`, complete the PM-003A non-blocking UX debt while adding generation:
- visual project scope editor for school + term + phase;
- rule edit, duplicate, enable/disable actions;
- real `توليد الجدول` button enabled only when ready;
- solve progress/status card;
- candidate selector: البديل 1/2/3;
- week tabs for project-global weeks;
- readable timetable preview by day/time showing subject/teacher/section/resource labels;
- candidate penalty summary and soft-rule violations;
- infeasible/error state with factual diagnostics.

No drag/drop editor yet.

## 9. Display data
Candidate API should resolve enough labels for the UI without forcing the browser to reverse-engineer IDs:
- assignment/subject;
- teacher names;
- section names;
- resource names;
- school;
- week/day/start/end.

Keep IDs in the payload for future editing.

## 10. Tests
Preserve all existing tests and add at least:
- one-school feasible timetable places every occurrence once;
- impossible teacher overlap is prevented;
- shared teacher across two schools cannot overlap by real time even when period numbers differ;
- combined sections are placed once and block every included section;
- co-teaching blocks every included teacher;
- split assignments remain independently placeable;
- exclusive resource collision prevented;
- non-exclusive/shareable resource is not incorrectly treated as exclusive if supported by model;
- attendance mode does not remove teacher collision;
- required/forbidden/unavailable hard rules enforced;
- preferred/avoided soft rules affect objective and penalty breakdown;
- 3 candidate generation produces distinct placement signatures when alternatives exist;
- deterministic seed regression;
- preflight-blocked project cannot start solve;
- infeasible versus time-limit/unknown status distinction;
- input fingerprint stable for same problem and changes when relevant input changes;
- persisted candidate entries reload correctly;
- only one active solve run per project;
- Web generation flow and candidate switching.

Use small deterministic fixtures so CI remains fast.

## 11. Performance guardrails
Default solve time limit should be modest for this phase, e.g. 10 seconds, configurable and bounded (1..60 seconds via API). CI fixtures should solve in seconds, not consume the full limit.

Do not optimize prematurely for huge schools; correctness first, but avoid obvious O(occurrences² × slots²) constructions when a conflict-index grouping can be used.

## 12. Out of scope
Do not implement in PM-003B:
- drag/drop, swap, locks, undo/redo;
- minimal-change repair;
- advanced distribution/consecutive rules beyond existing foundational catalog entries already modeled;
- AI natural-language rule creation;
- waiting/substitution;
- publishing/PDF/Excel;
- full explanation engine.

## Acceptance
PM-003B is accepted when a project marked ready can generate at least one real persisted collision-free timetable via CP-SAT, normally returns up to three distinct candidates, respects all foundational hard constraints and soft time weights, shows the candidates in `/timetables`, and all PostgreSQL/Python/Web CI gates remain green.

Required commit:
`feat: generate first CP-SAT timetable candidates`

Do not start PM-003C/editor work until review.