# PM-002C Review Notes

PM-002C is substantially successful: term scoping, SectionOffering, relational teacher/section/resource relationships, coverage/workload semantics, combined sections, co-teaching, split assignments, the matrix UI, advanced list, and CI all exist. Review still found several correctness gaps that should be repaired before PM-002D.

## 1. Bulk “fill from curriculum” must fill the remaining demand
The current bulk service uses the full `CurriculumRequirement.weekly_occurrences` as the new assignment count. That is unsafe for a partially assigned cell.

Example:
- required = 6
- already assigned = 4
- user selects “تعبئة العدد المطلوب من المنهج”

Expected new assignment count: `2`.
Current behavior can create `6`, making the cell `10/6`.

Required behavior:
- compute existing assigned coverage for each selected offering + subject in the selected term;
- remaining = required - assigned;
- if remaining > 0, use remaining;
- if complete/over, do not silently add another full requirement; return/preview a clear skip/conflict state;
- do not mutate CurriculumRequirement.

Add API regression tests for missing, partial, complete, and over cells.

## 2. Bulk/cell preview must be factual and server-derived
The bulk dialog currently previews only the number of affected sections. For safe assignment work, preview the actual projected effect before mutation:
- required / currently assigned / delta / projected assigned / projected status per cell;
- teacher current workload / delta / projected workload / limit warning;
- combined-section and co-teaching semantics must match persisted calculations.

Prefer a typed preview/dry-run service/endpoint that reuses the same validation/calculation code as save. Do not fabricate authoritative warnings only in React.

The individual cell editor should likewise expose projected impact before final save when the proposed count/teachers/sections changes.

## 3. Existing assignments that reference a resource must not enter a dead-end when the resource is deactivated
Master-data update currently allows `Resource.is_active=false` while assignments reference it, while the assignment snapshot exposes only active resources and assignment validation rejects inactive resources even when unchanged on an existing assignment.

Choose and implement one consistent lifecycle policy. Preferred simple policy for now:
- block deactivation of a resource while any teaching assignment references it, with a structured dependency conflict;
- keep delete protection relational as already implemented.

Alternatively, if inactive referenced resources are allowed, they must remain visible in assignment snapshots/editors and unchanged existing references must be preservable while new references are blocked. Do not silently drop a resource from an assignment when editing another field.

Add API + Web regression coverage.

## 4. Legacy JSON backfill must accept only same-tenant/same-school valid relationships
The PM-002C migration should not blindly turn arbitrary legacy JSON section/resource IDs into relational rows.

Before backfilling:
- section must resolve through grade/stage to the assignment tenant + school;
- resource must belong to the assignment tenant + school;
- invalid/cross-school IDs must be skipped or cause an explicit diagnostic according to the migration policy;
- never create a SectionOffering whose school/tenant metadata contradicts the referenced Section hierarchy.

Add migration-oriented regression coverage where practical.

## 5. Bulk payload relation uniqueness
Reject duplicate `section_offering_ids`, duplicate `assignment_ids`, and duplicate `teacher_ids` in bulk request schemas rather than allowing duplicate operations to be executed repeatedly.

## Acceptance gate for PM-002C repair
Before PM-002D:
- partial bulk fill adds only remaining demand;
- complete/over cells are not accidentally overfilled;
- projected bulk/cell effects are shown from server-derived facts before commit;
- resource deactivation cannot strand existing assignments;
- migration backfill cannot create cross-school/cross-tenant relational links from legacy JSON;
- duplicate bulk IDs are rejected clearly;
- all previous tests and quality gates remain green;
- no Legacy files are changed.
