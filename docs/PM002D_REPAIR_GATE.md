# PM-002D Repair Gate

Read `docs/REVIEW_NOTES_PM002D.md` before editing.

PM-002D remains blocked until all four review findings are repaired:

1. same-job staged dependency resolution without authoritative preview writes;
2. group-key scalar consistency + aggregate PM-002C preview;
3. explicit, truthful update-mode before/after semantics;
4. PostgreSQL Alembic-from-empty + seed verification in GitHub Actions.

Do not begin solver, rule builder, availability, waiting/substitution, or later timetable-generation work until this gate is accepted.

Required commit message:
`fix: complete PM-002D import integrity gate`
