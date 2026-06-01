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

The browser receives only a lawdit first-party HttpOnly session cookie plus safe profile fields from `/api/auth/session`.

`X-Actor-Id` may still exist for local development compatibility. It is not authentication and must not override a valid authenticated session in prelaunch mode.

SQLite-backed prelaunch Sources, scans, findings, audit events, metrics, and evaluation state must be scoped by the first-party session `userId`. Cross-account object identifiers must resolve as not found or current-account empty state. Legacy global rows are quarantined outside authenticated account scopes during migration.

Legacy DOC/XLS/PPT extraction uses host-local LibreOffice headless conversion inside temporary directories. The converter boundary must not persist source bytes, converted raw text, LibreOffice profile data, private host paths, or raw detected values into public API payloads or validation reports.

Enterprise SSO, SCIM, production RBAC, tenant provisioning, and production authorization policy are deferred.

## Role Simulation

Permission and review roles remain represented through the permission-boundary contract. Authentication proves a browser user identity; it does not by itself grant deletion, tenant, connector, or review powers.

## Permission Boundary UX

P0 should expose allowed and denied actions to the UI. This improves user control without pretending that role simulation is production authorization.

## External Services

P0 must not require live Microsoft Graph, tenant secrets, or external deletion APIs.

Google and GitHub OAuth are approved only for prelaunch sign-in. They must not be used as directory sync, tenant inventory, or authorization providers in this slice.

Google Drive selected-source access is approved through the Google Picker prelaunch boundary and the account-level Drive binding documented in `docs/design/google-drive-account-binding.md`. The frontend may receive a short-lived Picker access token from browser OAuth or from the connected account binding only to open Picker and authorize the current runtime source selection; those access tokens must not be persisted. A signed-in user may also store a personal Drive binding in the local account store; its refresh token must stay server-side and must not appear in source records, SQLite workflow documents, logs, audit events, frontend payloads, or UI state. This binding is not tenant inventory, production authorization, or source-file deletion authority.

Direct HTTPS file links are approved only for public BOM/charset-aware Unicode text-like, XML, JSON/JSONL/NDJSON, RTF, EML/RFC 5322 email, bounded ZIP archives, PDF text-layer or bounded local PDF OCR candidate, Office Open XML, OpenDocument, supported image, supported transcript, or bounded raw video media files. The backend must reject non-HTTPS links, embedded credentials, private-address hosts, unsupported content, and over-limit files before storing workflow output. Email extraction must skip attachments and must not expose raw body text, raw header values, or attachment names in public selectors. ZIP extraction must not write members to disk, must not recursively expand nested archives, and must not expose raw member names in public selectors. Image, PDF OCR, and video frame OCR must run locally through host OCR tooling when `LAWDIT_OCR_MODE=local`; `LAWDIT_OCR_LANGS` may select installed Tesseract language packs. Raw video media additionally requires host-local FFmpeg, must use temporary frame files only, and must not expose raw frames, raw media, raw OCR text, or audio in public payloads.

## Public Upload Trial

The public upload-analysis trial is implemented as the narrow boundary documented in `docs/design/public-upload-analysis-preview.md`. It enforces server-side size validation, a 10 MB maximum file limit, one active file per browser trial session, a 10-active-analysis global cap in the API process, safe filename handling, server-side content validation, transient in-memory raw-file handling, capacity release on every terminal state, and redacted result output. The trial must not expose raw sensitive values, legal advice, full GDPR-compliance claims, automatic deletion, production tenant access, durable queue state, or Microsoft Graph integration.

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
