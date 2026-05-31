# Security and Privacy Notes

## P0 Safety Boundary

The hackathon prototype must simulate deletion. It must not delete, quarantine, alter, or remotely move real user files.

## Sensitive Data Handling

- Mock snippets must be redacted.
- Evidence examples must not contain real personal data.
- UI examples should show masked values, such as `[REDACTED]` or `DE** ****`.
- Raw extracted text is not part of the public API contract.
- Prelaunch source readers must not persist raw source files or provider access tokens; they may persist metadata, redacted snippets, findings, metrics, and audit events.
- Audit examples should include decision metadata, not raw sensitive content.
- Human-entered audit reason text should be sanitized before public display; audit events must preserve accountability without becoming a new store of raw personal data.

## Authentication

Prelaunch sign-in uses backend-owned Google and GitHub OAuth authorization-code flows. Provider client secrets, provider access tokens, refresh tokens, auth state, and PKCE verifier must stay server-side and must not be returned to the frontend.

The browser receives only a DataSentinel first-party HttpOnly session cookie plus safe profile fields from `/api/auth/session`.

`X-Actor-Id` may still exist for local development compatibility. It is not authentication and must not override a valid authenticated session in prelaunch mode.

SQLite-backed prelaunch Sources, scans, findings, audit events, metrics, and evaluation state must be scoped by the first-party session `userId`. Cross-account object identifiers must resolve as not found or current-account empty state. Legacy global rows are quarantined outside authenticated account scopes during migration.

Enterprise SSO, SCIM, production RBAC, tenant provisioning, and production authorization policy are deferred.

## Role Simulation

Permission and review roles remain represented through the permission-boundary contract. Authentication proves a browser user identity; it does not by itself grant deletion, tenant, connector, or review powers.

## Permission Boundary UX

P0 should expose allowed and denied actions to the UI. This improves user control without pretending that role simulation is production authorization.

## External Services

P0 must not require live Microsoft Graph, tenant secrets, or external deletion APIs.

Google and GitHub OAuth are approved only for prelaunch sign-in. They must not be used as directory sync, tenant inventory, or authorization providers in this slice.

Google Drive selected-source access is approved only through the Google Picker prelaunch boundary. The frontend may request a short-lived access token for selected files or folders, and the backend may use that token only for the current scan request. The token must not be stored in source records, SQLite workflow documents, logs, audit events, or frontend payloads.

Direct HTTPS file links are approved only for public text-like, PDF text-layer, Office Open XML, supported image, supported transcript, or recognized raw video media files. The backend must reject non-HTTPS links, embedded credentials, private-address hosts, unsupported content, and over-limit files before storing workflow output. Image OCR must run locally through the host OCR binary when `DATASENTINEL_OCR_MODE=local`, and raw video media must stay hard/OCR-deferred until an approved local media processor exists.

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
