# PM-002C Review Acceptance

PM-002C and its repair gate are accepted after review of commit `065953e9c20c16c8dd041250cd348d27928b03da` and successful CI.

Accepted invariants:
- assignments are tenant/school/term scoped;
- SectionOffering binds section + term + shift;
- teacher/section/resource assignment relationships are relational;
- combined sections, co-teaching, and split assignments preserve correct coverage/workload semantics;
- curriculum coverage and teacher workload are computed from persisted relational data;
- bulk curriculum fill adds only remaining demand and skips complete/over cells;
- individual and bulk previews are server-derived before mutation;
- referenced resources cannot be deactivated into an editing dead-end;
- bulk duplicate IDs are rejected;
- legacy JSON backfill validates same-tenant/same-school section/resource scope;
- specialty remains descriptive and never blocks assignment;
- prior regression suites remain green.

PM-002D may now begin. Do not weaken these invariants while adding imports.