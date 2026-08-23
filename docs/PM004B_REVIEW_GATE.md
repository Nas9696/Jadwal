# PM-004B Review Gate — Arabic Natural-Language Scheduling Assistant

Accept PM-004B only if:

1. Free text never writes a SchedulingRule directly; parse/preview is zero-write.
2. Every proposal is validated by the existing typed rule registry and project/tenant reference validation.
3. Ambiguous or unresolved entity references never auto-merge or auto-select silently.
4. Hard vs soft wording is represented explicitly and shown before confirmation.
5. Confirmation is explicit and bound to the exact preview; tampering/stale preview is rejected.
6. Confirmed rules are persisted through the same authoritative rule service used by the manual Rule Builder.
7. The deterministic Arabic parser works in CI without external network/API credentials.
8. Optional LLM/provider output, if implemented, is treated as untrusted structured input and cannot invent IDs/types or bypass validation.
9. Confirmed rules immediately affect preflight, solver, quality, editor move analysis and explanations through the existing rule engine.
10. Unsupported requests are reported as unsupported rather than approximated with the wrong rule.
11. Multiple proposals can be previewed and selectively confirmed.
12. Arabic RTL UX handles parse, clarification, preview and confirmation cleanly.
13. All PM-001 through PM-004A tests and PostgreSQL migration/seed CI remain green; Legacy remains untouched.

Do not open a repair gate for cosmetic issues. Block progression only for safety, incorrect rule creation, scope leakage, silent ambiguity, or materially broken assistant flow.
