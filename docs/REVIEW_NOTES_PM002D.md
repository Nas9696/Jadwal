# PM-002D Review Notes

PM-002D is substantially successful: ImportJob/ImportRow staging exists, CSV/XLSX parsing and security limits are present, Arabic/English header detection and mapping exist, row diagnostics and exclusion exist, canonical teacher linking is preserved, assignment imports are term-scoped, commit is transactional, replay/double-commit protection exists, the `/imports` workspace exists, and CI is green.

The review still found four blockers before PM-002D can be accepted and before solver/rule work begins.

## 1. Same-job staged dependencies are not resolved during validation

Validation currently resolves structure, subjects, teachers, resources, section offerings, and assignment references only from authoritative persisted domain tables. This means a single workbook/job cannot reliably contain a new Stage/Grade/Section plus a CurriculumRequirement or SectionOffering/TeachingAssignment that references those new staged rows, because validation marks the later rows as `reference_not_found` before commit has created the earlier dependencies.

This conflicts with the PM-002D requirement that one ImportJob can validate and commit related entities in dependency order without preview writes.

Required fix:
- build a deterministic staged planning/resolution layer (in-memory plan or staging overlay) during validate/preview;
- later rows may resolve references to earlier proposed `create`/`link` rows in the same ImportJob without writing authoritative tables;
- detect duplicate/ambiguous staged identities and turn them into row conflicts rather than guessing;
- add an end-to-end multi-sheet test that creates new structure + teacher + subject + resource + curriculum + offering + assignment in one job, proves preview makes zero authoritative writes, then commits successfully.

## 2. `group_key` needs group-level consistency validation and preview

Commit groups assignment rows by `group_key`, but currently takes the subject and weekly count from the first row and unions teachers/sections/resources from all rows. If another row in the same group has a different subject or weekly count, the commit can silently use the first row's values.

Required fix:
- validate each explicit group as one planned TeachingAssignment before it becomes ready;
- all rows in a group must agree on subject, term, weekly occurrences, and any other scalar assignment fields;
- conflicting group rows must be `conflict` with structured diagnostics;
- aggregate teacher/section/resource sets deliberately;
- run PM-002C preview/validation on the aggregated group so coverage/workload warnings match the actual committed assignment;
- add tests for inconsistent subject/count and for correct combined/co-teaching preview semantics.

## 3. Update mode is incomplete relative to its UI/contract

`allow_updates` currently changes existing CurriculumRequirement behavior, but existing teacher/subject/resource rows are generally marked `skip_unchanged` based on identity even when incoming mutable fields differ. The review gate requires that if update mode is offered, supported updates show field-level before/after changes and do not silently discard differences.

Required fix:
- define explicitly which stable-key entities support updates in PM-002D (at minimum curriculum; preferably teacher descriptive fields by canonical code, subject by code, and resource by code where safe);
- when incoming values differ, default safe mode should preserve existing data but show the difference rather than calling it unchanged;
- with explicit update mode, return `update` plus field-level `before_values`/`after_values` and commit through authoritative services;
- do not silently change canonical identity or reactivate archived entities;
- if an entity is intentionally not updateable through imports, return a clear conflict/warning rather than `skip_unchanged` when values differ.

## 4. PostgreSQL Alembic + seed is not actually part of CI

The current GitHub Actions `python` job runs Ruff, mypy, and pytest only. It does not start PostgreSQL, run the migration chain from an empty database, or execute the seed. Local inability to run Docker/PostgreSQL is therefore not compensated by CI, despite the PM-002D quality gate requiring Alembic-from-empty + seed verification.

Required fix:
- add a PostgreSQL service (or equivalent isolated PostgreSQL setup) to the Professional Manager CI Python job;
- wait for DB readiness;
- set the test/migration `DATABASE_URL` explicitly;
- run `alembic upgrade head` from an empty DB through all migrations;
- run the project seed against that migrated PostgreSQL DB;
- add a lightweight integrity assertion after seed (at minimum successful seed with FK constraints; preferably expected key row counts);
- keep normal unit tests as they are.

## Acceptance gate

PM-002D can be accepted when:
- one multi-sheet import can resolve newly staged dependencies without authoritative preview writes;
- explicit teaching groups cannot silently mix different subjects/counts and are previewed as the aggregate assignment that will be committed;
- update mode and before/after semantics match the visible contract;
- GitHub Actions proves the full PostgreSQL migration chain and seed on an empty DB;
- all prior tests remain green and Legacy remains untouched.
