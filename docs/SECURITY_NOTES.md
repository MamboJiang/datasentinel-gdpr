# Security and Privacy Notes

## P0 Safety Boundary

The hackathon prototype must simulate deletion. It must not delete, quarantine, alter, or remotely move real user files.

## Sensitive Data Handling

- Mock snippets must be redacted.
- Evidence examples must not contain real personal data.
- UI examples should show masked values, such as `[REDACTED]` or `DE** ****`.
- Raw extracted text is not part of the public API contract.
- Audit examples should include decision metadata, not raw sensitive content.
- Human-entered audit reason text should be sanitized before public display; audit events must preserve accountability without becoming a new store of raw personal data.

## Role Simulation

P0 may simulate roles with `X-Actor-Id`. This is not authentication. Production authentication and authorization are deferred.

## Permission Boundary UX

P0 should expose allowed and denied actions to the UI. This improves user control without pretending that role simulation is production authorization.

## External Services

P0 must not require live Microsoft Graph, production OAuth, tenant secrets, or external deletion APIs.

OpenRouter assistive AI is the only approved external AI boundary. It must follow these controls:

- The API key is stored only in ignored local environment files or host secret management.
- The key is never returned from `/api/health`, scan, metrics, evaluation, audit, or frontend payloads.
- AI calls require assistive mode, a configured key, redacted deterministic evidence, active policy-pack context, and a passing budget preflight.
- Fail-closed mode prevents model calls when OpenRouter usage cannot be checked.
- The 25 EUR project budget is represented by a 25 EUR config value and a conservative 25 USD OpenRouter credit cap.
- Raw extracted text, file bodies, page images, credentials, tenant tokens, or unredacted personal data must not be sent to OpenRouter.
- AI output is Atlas stage-4 operational context support only and must not be presented as legal advice, proof of GDPR compliance, owner assignment, permission decision, audit fact, or a deletion instruction.

## Review Safety

Any future production deletion path must include:

- Human approval.
- Retention check.
- Legal hold check.
- Audit event.
- Rollback or recovery story.
- Explicit design note before implementation.

## Law-Agnostic Structure

Scanner and review workflow code should consume policy-pack guidance. It should not hard-code one current legal interpretation as permanent structure.
