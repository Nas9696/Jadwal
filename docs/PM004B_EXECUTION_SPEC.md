# PM-004B Execution Spec — Arabic Natural-Language Scheduling Assistant

## Goal
Complete Phase 4 with a safe Arabic-first assistant that converts natural-language timetable instructions into typed existing `SchedulingRule` proposals. The assistant must never write rules directly from free text; it parses, resolves references, validates against the authoritative rule registry, previews the exact rule(s), and requires explicit confirmation before persistence.

This is a focused phase. Do not delay it for waiting/substitution, publishing, notifications, or Noor/Madrasati integration.

## Core flow
Inside `/timetables` add an assistant entry such as «اكتب طلبك».

Example commands:
- «لا تضع للأستاذ أحمد الحصة الأولى يوم الأحد»
- «يفضل أن تكون الرياضيات في أول ثلاث حصص»
- «وزع رياضيات أول أ على أربعة أيام على الأقل»
- «لا تجعل للأستاذ علي أكثر من 4 حصص في اليوم»
- «ضع حصتي العلوم متتاليتين»
- «اجعل إسناد الرياضيات قبل إسناد النشاط»

Flow:
1. User submits Arabic text.
2. Server normalizes text and resolves project-scoped entities.
3. Parser/provider returns structured rule proposal(s), never authoritative rules.
4. Server validates each proposal using the same `RULE_REGISTRY`, selector validation, project/tenant scope, parameter schemas, and severity rules already used by manual Rule Builder.
5. Return a confirmation preview in friendly Arabic showing resolved entities, rule type, hard/soft semantics, weight if relevant, exact parameters, warnings/ambiguities, and the source text.
6. User explicitly confirms selected proposals.
7. Server persists through the existing authoritative `save_rule` path.

No free-text command may bypass Rule Builder validation.

## Provider architecture
Create an abstraction such as `NaturalLanguageRuleParser` / provider interface.

Required production-safe behavior:
- A deterministic parser/resolver for common Arabic patterns covered by tests must work without external API credentials.
- Keep an optional provider seam for a configured LLM later or now if credentials exist, but CI and core functionality must not depend on external network calls.
- Any external/provider output is untrusted structured input and must pass exactly the same server-side registry/reference validation as deterministic parsing.
- Never allow a provider to invent entity IDs or unsupported rule types silently.

Do not hard-code an OpenAI secret in source or CI.

## Entity resolution
Resolve only inside the selected timetable project/tenant/term scope.

Support references to at least:
- teachers by canonical code or unique normalized name;
- subjects by code or unique normalized name;
- sections/classes by their scoped labels/codes;
- assignments by subject + section/teacher context when uniquely resolvable;
- resources by code/name where relevant.

If a reference is ambiguous, return `needs_clarification` with typed choices. Do not guess.
If no match exists, return `unresolved_reference`.
Cross-school/cross-tenant references must be rejected.

## Language handling
Arabic-first normalization should tolerate common variants:
- Arabic digits and Western digits;
- hamza/alef variants and whitespace;
- الحصة الأولى/الأولى/1/رقم 1;
- الأحد/يوم الأحد;
- مدرس/معلم/الأستاذ;
- soft expressions: يفضل، حاول، قدر الإمكان;
- hard expressions: لا تضع، يجب، ممنوع، يلزم.

Do not over-normalize proper names into unsafe matches.

## Proposal model
Return typed data such as:
- `source_text`
- `status`: ready / needs_clarification / unsupported / invalid
- `proposals[]`
  - rule_type
  - severity
  - weight
  - selector
  - parameters
  - resolved_labels
  - arabic_summary
  - confidence or parser evidence (informational only; never used to bypass validation)
- `clarifications[]`
- `warnings[]`

A proposal ID/token should bind confirmation to the exact preview payload so it cannot be altered client-side before confirmation. Prefer persisted short-lived draft rows or a signed/hash-bound preview with server-side revalidation.

## Confirmation/persistence
Provide endpoints along these lines:
- POST `/api/v1/timetable-projects/{project_id}/assistant/parse`
- POST `/api/v1/timetable-projects/{project_id}/assistant/confirm`

Confirmation must:
- revalidate project/tenant scope;
- revalidate registry schemas and references;
- persist only proposals explicitly selected/confirmed;
- use existing rule service semantics;
- reject stale/changed preview tokens;
- return created rule IDs and Arabic summaries.

Do not auto-confirm based on confidence.

## Multiple rules
One sentence may create multiple proposals when explicitly requested, e.g.:
«لا تضع أحمد الأحد الأولى ولا الثلاثاء الأخيرة».
Preview each rule separately and allow deselection before confirmation.

## Unsupported requests
If the user asks for a rule not in the current registry, return a factual `unsupported_rule_request` and explain that it is not yet supported. Do not emulate it with a different rule.

## Explainability integration
After confirmation, the created rule must immediately participate in:
- preflight;
- CP-SAT generation;
- quality report;
- move analysis;
- placement explanations.

No assistant-only shadow rule store.

## UX
Arabic RTL assistant panel should include:
- examples/suggestions;
- text box and submit;
- loading/error/empty states;
- clarification choices when ambiguous;
- preview cards with friendly rule sentence and hard/soft badge;
- edit via normal Rule Builder before confirmation if desired;
- explicit «اعتماد القواعد» button;
- success state linking to created rules.

Never use browser `alert/prompt/confirm`.

## Audit and safety
Persist assistant source/provenance on audit metadata or a small assistant draft/audit model if useful, without duplicating the authoritative rule definition.
Log parser/provider type and created rule IDs; do not log secrets.

## Tests
Preserve all existing tests and add at least:
- Arabic teacher unavailable command;
- Arabic subject preferred-time command;
- Arabic max-lessons-per-day command;
- Arabic minimum-days distribution command;
- consecutive double lesson command;
- relationship/before command;
- Arabic and Western digits;
- hard vs soft wording;
- unique teacher/subject/section resolution;
- ambiguous teacher => clarification, no rule write;
- unresolved reference => no write;
- cross-tenant/cross-school rejected;
- unsupported rule request => no substitute rule;
- parse preview performs zero rule writes;
- confirmation persists through authoritative validation;
- tampered/stale confirmation rejected;
- multiple proposals with selective confirmation;
- confirmed rule changes preflight/solver behavior in a small deterministic fixture;
- Web assistant parse/clarify/preview/confirm flow.

## Quality gates
Keep PostgreSQL CI and run all existing Python/API/Scheduler/Web/Ruff/mypy/ESLint/TypeScript/Next build/Alembic/seed checks.

## Out of scope
Do not start:
- waiting-duty/absence/substitution;
- PDF/Excel/image publishing;
- notifications;
- Noor/Madrasati APIs;
- autonomous rule changes without confirmation.

## Acceptance
PM-004B is accepted when a non-technical Arabic user can express common timetable constraints in natural language, receive an exact typed preview with ambiguity handling, explicitly confirm it into the existing authoritative rule engine, and the resulting rule affects the same preflight/solver/editor/explanation paths as manually created rules.

Required commit:
`feat: add Arabic natural-language scheduling assistant`
