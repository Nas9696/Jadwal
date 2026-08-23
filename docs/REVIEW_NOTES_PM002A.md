# PM-002A Review Findings

PM-002A is materially successful and its server-side school/tenant validation is a good base, but three user-facing/domain issues must be corrected before PM-002B.

## 1. Current academic year invariant
The current UI creates every new academic year with `is_current=true`, while the service/model do not ensure only one current year per school. The product must have at most one current year per school. Setting a year current must atomically clear the previous current year in the same school/tenant. Add server-side tests; do not rely on React state.

## 2. Complete edit workflow
The API exposes PUT, but most setup entities are only add/delete in the UI. PM-002A acceptance requires real CRUD. Provide a consistent edit experience for academic years, terms, shifts, school days, day blocks, stages, grades and sections (week patterns already have a limited edit path). Avoid browser `prompt()` as the primary professional editing UX; use an accessible inline form, drawer or modal and preserve server validation.

## 3. Day timeline must be scoped to the selected school day
The current timeline renders the full `blocks` collection for the school. When multiple SchoolDay records exist, blocks from different days/patterns/shifts can appear mixed in one timeline. Introduce explicit selected-day state, filter the timeline to `school_day_id`, and calculate default/new `block_order` within that selected day. Switching the selected day must show only that day's persisted blocks.

## Acceptance
- One school cannot end with two `is_current=true` academic years through API/UI.
- All PM-002A setup resource types that support update in the API have discoverable editing UI.
- No primary edit flow depends on `prompt()`/`alert()`.
- Timeline shows exactly one selected SchoolDay and never mixes other days.
- Add regression tests for the three findings.
- Preserve tenant/school validation, calendar invariants and all previous tests.
- Do not start PM-002B until this review gate passes.
