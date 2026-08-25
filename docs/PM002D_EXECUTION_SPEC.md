# PM-002D Execution Spec — Smart Excel/CSV Import

## Goal
Build a safe, Arabic-first import workspace that lets a school administrator bring existing school data into Professional Manager from Excel (`.xlsx`) and CSV without requiring fixed column order or exact header names. Import is a staged workflow: upload → detect → map → validate → preview → commit → results.

The import subsystem must reuse the authoritative service/domain rules already implemented. It must never bypass tenant/school/term validation, teacher canonical identity, assignment relationships, curriculum coverage rules, or dependency protections.

## Scope
PM-002D includes imports for:
- teachers and school memberships;
- subjects;
- academic structure: stages, grades, sections;
- curriculum requirements;
- resources;
- section offerings for a selected term/shift;
- teaching assignments, including a safe representation for simple, split, combined-section, and co-teaching data when the source provides grouping information.

PM-002D does not include:
- automatic timetable solving;
- Rule Builder / teacher availability;
- Noor/Madrasati scraping or unauthorized integration;
- direct writes to external systems.

Official exports from Noor/Madrasati may be imported as ordinary files when the user is authorized to possess/export them. Do not hardcode or claim an official integration unless an authorized API exists later.

## 1. Import architecture and staging
Create explicit import staging models, e.g.:
- `ImportJob`: tenant, school, optional target term, file metadata/hash, status, detected entity/sheets, mapping, validation summary, committed_at, result summary;
- `ImportRow` or an equivalently safe staging model: job, sheet/name, source row number, normalized source values, proposed action, diagnostics. JSON is acceptable for staging payload because it is not authoritative domain state.

Suggested job states:
`uploaded`, `mapped`, `validated`, `ready`, `committed`, `failed`, `cancelled`.

A committed job must be idempotent: the same job cannot be committed twice. Re-uploading the same file may create another job, but the UI should warn when the same file hash/target has already been committed recently.

Preview and validation must not write authoritative school data.

Commit must be atomic per ImportJob: if an unexpected authoritative write fails, roll back the whole job and keep diagnostics; do not partially import silently.

## 2. File support and security
Support:
- `.xlsx` using a server-side parser such as openpyxl;
- `.csv` with UTF-8 / UTF-8 BOM and safe delimiter detection for comma/semicolon/tab where practical.

Treat all uploads as untrusted:
- configurable max file size (default around 10 MB);
- configurable max rows (default around 20,000 total parsed rows) and sheets (e.g. 30);
- reject unsupported binary `.xls`, macro-enabled `.xlsm`, executable/archive masquerading, or mismatched content types;
- do not execute macros or formulas;
- detect formula cells in authoritative mapped fields and reject/warn instead of evaluating formulas as trusted input;
- for XLSX inspect zip entry count/expanded size before loading to reduce zip-bomb risk;
- never use user filenames as filesystem paths;
- sanitize/normalize text lengths before persistence;
- temporary upload bytes should not become permanent documents by default.

## 3. Header recognition and mapping
Column order must never matter.

Implement normalized header recognition with Arabic/English aliases. Examples:
- teacher name: `اسم المعلم`, `المعلم`, `teacher`, `teacher name`;
- canonical code: `رقم المعلم`, `الكود`, `teacher code`, `employee id`;
- subject: `المادة`, `اسم المادة`, `subject`;
- stage/grade/section: `المرحلة`, `الصف`, `الشعبة`, `stage`, `grade`, `section`;
- weekly occurrences: `الحصص`, `عدد الحصص`, `النصاب الأسبوعي`, `weekly lessons`;
- resource: `المعمل`, `الغرفة`, `resource`, `room`;
- shift: `الفترة`, `الشفت`, `shift`.

Normalization should handle whitespace, punctuation, Arabic letter variants where safe, and case-insensitive English.

Automatic detection is a suggestion only. UI must show a mapping screen and allow the user to override source-column → target-field mapping before validation.

Reject ambiguous duplicate mapping where two source columns map to one exclusive target field unless explicitly supported.

## 4. Entity detection
A workbook may contain multiple sheets. Detect likely entity type per sheet based on headers and confidence, but require explicit user confirmation when confidence is low or multiple entity types are plausible.

Allow the user to skip sheets.

Provide Arabic template downloads/examples for supported entity types. Templates are conveniences, not mandatory input formats.

## 5. Matching and proposed actions
Every staged row must show a proposed action such as:
- `create`;
- `link_existing`;
- `update` (only when explicitly permitted by user import mode);
- `skip_unchanged`;
- `warning`;
- `conflict`.

Do not silently overwrite existing records.

Default safe import mode is create/link missing data and preserve existing data. If update mode is offered, show field-level before/after changes and require confirmation.

### Teachers
Teacher identity is canonical at tenant scope.
- Match by canonical code first.
- If canonical code matches an existing teacher, link/update membership according to explicit rules; do not create a duplicate Teacher.
- If code is absent, an exact normalized unique name may be suggested, but ambiguous name matches must require user resolution and must not silently merge people.
- Existing inactive canonical teacher/membership must follow PM-002B lifecycle rules; do not reactivate silently.
- Specialty is descriptive only.

### Subjects/resources
Prefer school-scoped code match, then unique exact normalized name as a suggestion. Ambiguous name matches are conflicts.

### Academic structure
Resolve hierarchy explicitly:
`Stage → Grade → Section`.
Never attach a grade/section to a similarly named entity from another school/tenant.

### Curriculum requirements
Resolve grade + subject in the selected school. Import weekly demand without changing existing demand silently.

### Section offerings
Require a target term and resolve section + shift in the same school. Do not guess a shift when multiple shifts exist unless the file explicitly maps it or the user chooses a default in the mapping workflow.

### Teaching assignments
Require a selected target term.
Resolve subject, active teacher membership(s), section offering(s), resource(s) through authoritative IDs after matching.
Do not create cross-school/cross-term references.

Support an optional source `group key`/`teaching group` column. Rows sharing a group key may intentionally form one assignment with multiple teachers and/or sections. Without a group key, default each row to an independent assignment; do not guess combined/co-teaching groups merely because fields look similar.

Split assignments are allowed as existing PM-002C semantics permit.

## 6. Validation and diagnostics
Validation must be server-side and return structured row-level diagnostics:
- sheet;
- row number;
- field/column where relevant;
- severity: error/warning/info;
- machine code;
- Arabic-friendly message key/text;
- suggested resolution where possible.

Examples:
- missing required field;
- invalid weekly count;
- duplicate code within file;
- duplicate row;
- ambiguous teacher match;
- teacher archived;
- membership inactive;
- subject/resource inactive;
- grade/section hierarchy not found;
- shift missing for term offering;
- cross-school candidate/reference;
- assignment would exceed curriculum (warning);
- teacher workload would exceed planning limit (warning).

Errors block commit. Warnings may allow commit after user acknowledgement.

For assignment rows, reuse PM-002C preview/validation logic rather than reimplementing coverage/workload rules in the importer.

## 7. Preview UX
Create `/imports` as an Arabic RTL stepper/workspace.

Steps:
1. اختر المدرسة والفصل الدراسي عند relevant import types.
2. ارفع الملف (drag/drop + file picker).
3. استعرض الأوراق/نوع البيانات المكتشف.
4. طابق الأعمدة.
5. تحقق من البيانات.
6. راجع المعاينة.
7. تأكيد الاستيراد.
8. النتائج.

Preview should include:
- total rows;
- valid rows;
- warnings;
- errors;
- create/link/update/skip/conflict counts;
- searchable/filterable row table;
- field-level before/after for proposed updates;
- assignment coverage/workload warnings where applicable.

Do not make the user fix thousands of errors one modal at a time. Support filtering by error type and show source row number clearly.

Allow excluding individual rows from commit when they are otherwise valid, but exclusion must be explicit and visible.

## 8. Commit ordering and atomicity
Within one job, resolve dependencies in deterministic order, for example:
1. stages;
2. grades;
3. sections;
4. teachers/memberships;
5. subjects;
6. resources;
7. curriculum requirements;
8. section offerings;
9. assignments.

The importer must use the same authoritative service layer or shared domain functions as normal UI writes. Do not duplicate relaxed insert logic just for imports.

If all validated rows cannot be committed consistently, roll back and report the exact failure.

## 9. Audit/result summary
Persist ImportJob metadata and final summary:
- source filename display name;
- SHA-256 hash;
- uploaded/validated/committed timestamps;
- user/actor placeholder compatible with future auth/RBAC;
- target school/term;
- counts created/linked/updated/skipped;
- warnings/errors;
- final status.

Do not permanently persist raw source file bytes unless explicitly required later.

## 10. Templates
Provide safe downloadable CSV templates at minimum for:
- teachers;
- subjects;
- academic structure;
- curriculum requirements;
- resources;
- assignments.

Arabic headers should be the default. English examples may be documented.

## 11. API direction
Use typed endpoints, not one arbitrary upload endpoint with opaque behavior. A reasonable shape:
- create/upload import job;
- inspect sheets/detection;
- save mapping;
- validate;
- preview/list rows;
- commit;
- get job/result;
- cancel/delete uncommitted staging job;
- download template.

Multipart upload is appropriate for the file bytes. All subsequent operations use the ImportJob ID and remain tenant/school scoped.

## 12. Required tests
Preserve all prior tests.

Add API/service tests for at least:
- Arabic headers in arbitrary order;
- English aliases;
- CSV UTF-8 BOM and delimiter handling;
- XLSX sheet detection;
- unsupported/macro/binary file rejection;
- file/row/sheet limits;
- formula cell rejection/warning in authoritative fields;
- preview causes zero authoritative writes;
- teacher canonical-code match links existing identity without duplicate;
- ambiguous teacher name does not silently merge;
- inactive teacher/membership lifecycle respected;
- cross-school subject/resource/section rejected;
- hierarchy matching is school scoped;
- curriculum requirement proposed create/update conflict behavior;
- assignment import uses selected term and active memberships;
- group key forms combined/co-teaching only when explicit;
- split assignments remain valid;
- assignment preview warnings reuse PM-002C semantics;
- duplicate rows within file diagnosed;
- commit is atomic and job cannot be committed twice;
- same-file hash warning/replay protection behavior;
- row exclusion is respected;
- committed results survive reload.

Add Web tests for:
- upload step;
- detection/mapping override;
- validation summary;
- error filtering/row numbers;
- preview counts/actions;
- confirmation before commit;
- final result summary;
- template links;
- school/term scoping;
- Arabic RTL/accessibility states.

## 13. Quality gates
Run:
- Python/API/Scheduler tests;
- Ruff;
- mypy;
- Web tests;
- ESLint;
- TypeScript;
- Next.js production build;
- Alembic from an empty DB through all migrations;
- seed with Foreign Keys enabled.

No Legacy files may be changed.

## Acceptance criteria
PM-002D is complete when a school administrator can upload a non-fixed-order Arabic or English XLSX/CSV, confirm automatic column mappings, validate row-level issues, preview create/link/update/skip decisions and assignment warnings without modifying authoritative data, then commit a valid import atomically and reload a durable result summary. The importer must preserve all tenant/school/term and assignment invariants already established.

## Commit
Use:
`feat: build smart Excel CSV import workspace`

Do not begin solver/rule work until PM-002D review is accepted.