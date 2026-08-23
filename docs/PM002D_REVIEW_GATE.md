# PM-002D Review Gate

PM-002D must not be accepted merely because a file can be uploaded and parsed.

Review must verify:

1. Uploads are treated as untrusted and file/type/size/row/sheet/formula limits are enforced server-side.
2. Column order does not matter and Arabic/English aliases produce suggestions, not silent irreversible decisions.
3. Mapping can be overridden before validation.
4. Preview/validation performs zero authoritative domain writes.
5. Row diagnostics include sheet/row/field/severity/code and are useful in Arabic UX.
6. Teacher matching preserves one canonical Teacher and never silently merges ambiguous names.
7. Inactive teacher/membership rules from PM-002B-R remain enforced.
8. Stage/grade/section matching cannot cross school/tenant hierarchy.
9. Curriculum requirement imports do not silently overwrite existing demand.
10. Assignment imports require explicit term scope and reuse PM-002C validation/preview semantics.
11. Combined/co-teaching import grouping happens only from explicit source group keys or explicit user mapping, never guesswork.
12. Commit is atomic and a committed ImportJob cannot be committed twice.
13. Same-file replay/duplicate warning is present.
14. Existing data is not overwritten silently; update mode shows field-level proposed changes.
15. Template downloads are safe and do not become the only accepted format.
16. Final ImportJob result is durable and reloadable.
17. All prior PM-001 through PM-002C-R tests remain green.
18. No Legacy files are changed.

Do not begin solver/rule implementation until this review gate is accepted.