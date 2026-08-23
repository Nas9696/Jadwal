# PM-002B Review Acceptance

PM-002B and PM-002B-R are accepted after review of commit `e1b77cef3358fc6c73c81da1d15d9affba8a7459`.

Accepted invariants:
- canonical teacher identity remains tenant-scoped and reusable across schools,
- inactive school memberships remain visible and can be reactivated without duplicate membership rows,
- linked-school metadata exposes the true home-school membership even when another school is being viewed,
- at most one active home-school membership is protected by service/database rules,
- archived canonical teachers cannot silently gain active school memberships,
- zero workload values remain valid values,
- unlink/dependency protection remains intact,
- PM-002B subject, curriculum requirement, and resource behavior remains preserved.

PM-002C may proceed only under `docs/PM002C_EXECUTION_SPEC.md`, including replacement of assignment section/resource JSON authority with relational assignment relationships.