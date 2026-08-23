# PM-006A Review Gate — Reporting and export

Accept PM-006A only if it produces trustworthy school outputs from authoritative data. Do not block acceptance for cosmetic polish that does not affect correctness, readability, or export usability.

## Must-pass functional gate
1. Reports default to the current WorkingTimetable, not an old candidate.
2. Candidate source is used only when explicitly requested.
3. General, section, teacher, subject/resource, daily substitution, and waiting-workload reports return typed display-ready data.
4. Teacher report covers the canonical teacher across all schools in the selected project without double counting.
5. Report rows preserve project-global week semantics and real start/end times.
6. Stale timetable revision is surfaced; exports do not silently mix revisions.
7. Tenant/project isolation is enforced server-side.
8. XLSX is a real workbook and Arabic headers/labels are readable.
9. PDF is a real PDF and Arabic RTL renders correctly.
10. PNG/image export is real and does not silently truncate multi-page output.
11. QR encodes the configured payload exactly.
12. Unsafe logo/content is rejected and temporary export artifacts are cleaned up.
13. Daily substitutions show covered and uncovered needs accurately from PM-005A authoritative state.
14. Waiting report preserves zero limits and combined teaching+substitution semantics.
15. `/reports` provides usable Arabic RTL preview, filters, print options, export states and errors.
16. Beta smoke flow proves the core product can produce usable outputs end-to-end.
17. No Legacy changes.
18. All prior tests remain green.
19. PostgreSQL CI from empty database, seed and integrity remain green.
20. Real PDF/image export runtime is exercised in CI if a new runtime dependency is introduced.

## Review emphasis
Treat these as blockers:
- wrong authoritative source;
- cross-tenant/project leakage;
- invalid/corrupt export files;
- broken Arabic/RTL PDF rendering;
- stale-revision data mixing;
- report rows calculated differently from the actual WorkingTimetable/substitution state;
- silent truncation;
- fake QR;
- export pipeline only mocked in CI.

Treat these as non-blocking unless severe:
- minor spacing/colors;
- extra report presets;
- advanced custom report designer features;
- additional branding themes;
- notification/share integrations not required by PM-006A.

## Acceptance evidence
Before acceptance, verify:
- implementation commit SHA;
- exact GitHub Actions run on that SHA;
- Python/Web test counts;
- PostgreSQL migration/seed job;
- sample service tests for XLSX/PDF/PNG signatures;
- current WorkingTimetable revision present in report metadata;
- no known functional blocker within PM-006A scope.
