# PM-006A — Reporting, print/export, and beta output gate

## Goal
Turn the now-operational timetable platform into a school-usable output workflow. A manager must be able to take the current authoritative WorkingTimetable, filter it into common school reports, print it cleanly in Arabic RTL, export it to PDF/Excel/image, and produce daily substitution/waiting outputs without reconstructing data outside Professional Manager.

This is a focused beta-output task. Do not expand into notifications, Noor/Madrasati APIs, Tauri, HR/payroll, or a generic report designer.

## Authoritative source
- Normal timetable reports default to the current `WorkingTimetable` for the selected project.
- A `TimetableCandidate` may be explicitly selected only for comparison/preview; never publish a candidate silently when a WorkingTimetable exists.
- Daily substitution/waiting reports use the current WorkingTimetable plus authoritative PM-005A absence/need/assignment state.
- Report generation must respect tenant/project/school scope and current timetable revision.
- A stale revision must be surfaced; never silently mix report rows from different timetable revisions.

## Report query model
Create typed server-side report contracts. React must not rebuild domain joins or calculate report rows independently.

At minimum support these report types:
1. `general_timetable` — whole project/school timetable.
2. `section_timetable` — one section/class.
3. `teacher_timetable` — one canonical teacher across all project schools.
4. `subject_timetable` — one subject.
5. `resource_timetable` — room/lab/resource usage.
6. `daily_substitutions` — absences, needs, assignments and uncovered lessons for a date/project week/day.
7. `waiting_workload` — teaching, substitution/waiting counts, remaining capacity and exemptions.

Useful filters:
- school
- stage/grade/section when applicable
- teacher/subject/resource
- project-global week
- weekday/date
- include/exclude remote/on-site labels as display only; attendance mode never changes collision semantics.

## Normalized report dataset
Build one typed report dataset that contains display-ready labels and structural metadata:
- report title/subtitle
- project/school/term labels
- source timetable id/version/revision
- generated timestamp
- project-global week and local week labels where useful
- rows/cells with day, start/end, optional period label, subject, teacher(s), section(s), resource(s), school, attendance label
- substitution-specific absent teacher, substitute, coverage status and reason/rank facts
- waiting-specific base workload, teaching workload, substitution count, effective limit, remaining capacity, exempt state

Do not expose raw opaque JSON as the only contract. Keep typed Pydantic schemas and stable API responses.

## Print layout
Add a dedicated Arabic RTL print workspace, for example `/reports`, with print-preview routes or components.

Required layout options:
- A4 and A3
- portrait and landscape
- color and monochrome
- compact and comfortable density
- show/hide school/project heading
- show/hide period time
- show/hide resource
- optional footer text
- signature lines/labels (e.g. timetable officer, school principal) as text placeholders
- repeat table headers across printed pages where applicable

Tables must remain readable when teacher/class names are long. Do not shrink text to unusable sizes merely to force one page.

## Branding and QR
Provide a small typed `ReportBranding`/settings model or equivalent project/school-scoped configuration, without building a generic CMS.

Support:
- school/project title override
- optional subtitle
- optional safe logo asset when configured
- optional QR payload/link
- footer text
- up to a few signature labels

QR must encode the real configured value, not a decorative placeholder.

Logo handling must be safe: validate file type/size, do not execute uploaded content, and do not use user filenames as storage paths.

## Export formats
### Excel
Generate real `.xlsx`, not HTML renamed to xlsx.
- Arabic sheet names/headers.
- sensible column widths.
- freeze panes when useful.
- one workbook may contain summary plus one sheet per selected teacher/section only when explicitly requested.
- no formulas are required for exported timetable facts.

### PDF
Generate a real PDF from the same print-report source so print and PDF do not drift semantically.
- Arabic RTL must render correctly.
- A4/A3 and orientation options must be respected.
- Do not create a separate business-logic implementation just for PDF.

A headless-browser print pipeline is acceptable if integrated reliably and covered in CI; a stable pure-library pipeline is also acceptable. Choose the least fragile approach for the current stack.

### Image
Export a real PNG image suitable for WhatsApp/mobile sharing.
- For multi-page reports, either return a ZIP of numbered PNG pages or a bounded explicitly selected page/view. Do not silently truncate.
- Keep Arabic text sharp/readable.

## Export API
Use typed endpoints such as:
- `POST /api/v1/timetable-projects/{project_id}/reports/preview`
- `POST /api/v1/timetable-projects/{project_id}/reports/export`

or equivalent REST structure.

The export request should include:
- report type
- filters
- source/current revision expectation
- format: `pdf | xlsx | png`
- paper/orientation/density/theme options where relevant
- branding options/preset id

Return correct content type and safe filename metadata. Never trust a user-supplied filename as a filesystem path.

## Performance and safety
- Bound report size/server work with clear limits.
- Avoid N+1 database queries for teacher/section/resource labels.
- Stream or buffer exports sensibly; do not write permanent files by default.
- Temporary files must be cleaned up.
- Tenant isolation on every report/export path.
- No cross-project entity references.

## Daily substitutions output
The daily report must make operations practical:
- absent teacher
- affected lesson
- assigned substitute or `غير مغطاة`
- school, section, subject, real time
- cancellation/coverage status
- optional score/rank explanation summary

Provide print/export for this view, not just on-screen rendering.

## Waiting workload output
Show at least:
- teacher
- contractual/base workload where available
- actual teaching workload in current timetable
- substitution/waiting count in relevant period
- effective combined limit
- remaining capacity
- exemption

Zero limits remain zero; never use truthiness fallback.

## Beta smoke flow
Add an end-to-end integration/smoke test fixture that proves the first public beta core workflow can complete without external services:
1. seed/create school data;
2. build a project and valid WorkingTimetable (it may reuse a small solved fixture rather than running a large solve);
3. retrieve general + teacher + section report datasets;
4. create at least one absence/substitution fact and retrieve daily report;
5. export at least XLSX and PDF (and PNG if pipeline permits within CI) and assert non-empty valid file signatures/content types;
6. verify source revision appears in output metadata.

Keep the fixture small and fast.

## Web UX
Add `/reports` or a clear reports area linked from `/timetables` and `/substitutions`.

Arabic RTL workflow:
`نوع التقرير → النطاق/الفلاتر → المعاينة → إعدادات الطباعة → تصدير`

Required states:
- loading
- empty
- validation error
- stale timetable warning
- export progress
- export failure

No browser `alert`, `prompt`, or `confirm`.

## Tests
API/service tests must cover at least:
- current WorkingTimetable is default authoritative source;
- candidate only when explicitly requested;
- teacher report across multiple project schools;
- section/general/resource report filtering;
- project-global week handling;
- long/Arabic display labels stay labels, not ids;
- stale revision rejection/warning contract;
- tenant/project isolation;
- daily substitution covered/uncovered rows;
- waiting workload 24/14 semantics and zero limits;
- real XLSX magic/structure;
- real PDF signature and non-empty pages;
- PNG signature or multi-page contract;
- QR contains configured payload;
- unsafe logo rejected;
- temporary export cleanup;
- beta smoke flow.

Web tests must cover:
- report type selection;
- filters;
- preview;
- paper/orientation toggles;
- teacher/class/general views;
- substitution report;
- export buttons and error states;
- Arabic RTL/accessibility.

## Quality gates
Preserve all PM-001 through PM-005A tests and PostgreSQL CI:
- PostgreSQL 16
- `alembic upgrade head` from empty
- seed
- integrity assertions
- Ruff
- mypy
- Python/API/Scheduler tests
- Web tests
- ESLint
- TypeScript
- Next.js production build

If PDF/image export adds a runtime dependency, CI must exercise the real pipeline rather than only mocking it.

## Out of scope
Do not start:
- email/push/WhatsApp notifications
- teacher self-service portal
- Noor/Madrasati live API adapters
- generic custom report designer
- Tauri desktop packaging
- additional Professional Manager modules

## Required commit
After all gates pass:
`feat: add timetable reporting and export workspace`

Push to `professional-manager-foundation` and stop for review.
