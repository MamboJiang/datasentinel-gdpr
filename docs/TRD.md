# Technical Requirements Document

## Current Technical Scope

This repository is initialized for documentation, collaboration, contract-first parallel delivery, and a controlled remote frontend plus P0 API preview. The approved technical baseline is the tolerant REST contract in `contracts/openapi.yaml`, its split schemas in `contracts/schemas/`, mock fixtures in `contracts/mocks/`, the local Python API server, optional local SQLite persistence for demo API state, the prelaunch Google/GitHub account boundary, the Workspace admin permission boundary, the optional OpenRouter AI assistive boundary, and the deployment path documented in `docs/DEPLOYMENT.md`.

No production database, queue, enterprise SSO, production RBAC, broad production file-source connector, or source-file deletion-capable deployment path is approved yet. The approved local storage boundary is the stdlib `sqlite3` file store documented in `docs/design/local-sqlite-persistence.md`; it is optional, local to the API process, and limited to restart-safe P0, prelaunch state, and local Workspace membership/invitation state. The approved external API boundaries are Google/GitHub OAuth for sign-in, Google Drive Picker and Drive API reads for user-selected files/folders, direct HTTPS text-like/PDF text-layer file reads, and the optional OpenRouter assistive AI path documented in `docs/design/openrouter-ai-processing.md`; OpenRouter is disabled unless explicitly configured and must not receive raw personal data.

## Technical Principles

- Keep implementation changes small, testable, and reversible.
- Prefer explicit boundaries between source connectors, classification, review workflow, audit logging, and presentation.
- Inject external collaborators into core logic instead of constructing them inside core modules.
- Keep side effects at boundary layers.
- Use behavior tests for user-observable contracts.
- Keep frontend and backend aligned through `OpenAPI-first + mock-first + vertical-slice-first`.
- Treat unknown fields and enum-like values as forward-compatible.

## Future Boundary Candidates

These are not approved implementation modules yet. They are candidate boundaries to evaluate before coding:

- Source connector boundary.
- Document extraction boundary.
- Finding classification boundary.
- Risk scoring boundary.
- Owner resolution boundary.
- Human review workflow boundary.
- Audit event boundary.
- Delta scan boundary.
- Evaluation harness boundary.
- Admin metrics boundary.
- Governance configuration boundary.
- Permission boundary boundary.
- Review support boundary.

## Backend Post-Source Planning

After a controlled sample source is connected, backend work should follow the planning sequence in `docs/design/backend-post-source-execution-plan.md`. Stage-level contracts are expanded in `docs/design/backend-post-source-stage-details.md`.

The sequence is:

1. Full scan orchestration.
2. Source inventory and extraction planning.
3. Deterministic signal detection.
4. Context classification and risk planning.
5. Owner routing.
6. Finding assembly and evidence card support.
7. Review support and permission boundary.
8. Human review command handling.
9. Audit event logging.
10. Delta scan planning.
11. Admin metrics aggregation.
12. Evaluation run planning.

This sequence is a planning contract, not an implementation approval. Each step must still be implemented as a narrow, behavior-tested task against the existing OpenAPI contract and mock fixtures.

## Full Scan Start Technical Slice

The approved first full-scan implementation is a frontend mock workflow slice, not a production scanner. It keeps the public API contract unchanged and uses the existing `StartFullScanRequest.sourceId` shape.

Technical constraints:

- Source readiness is evaluated from existing source status and the governance source-adapter model.
- Scan state, admin metrics, audit events, and evaluation summary update together in one explicit mock workflow boundary.
- The workflow must be covered by behavior tests for ready sources, not-ready sources, running state, completion state, and audit creation.
- No OCR, parser, AI model, paid service, database, queue, OAuth flow, Microsoft Graph integration, or deletion integration is introduced in this slice.
- Vitest is acceptable as the test runner because the frontend already uses Vite and the added dependency is development-only.

## Source Inventory and Content Extraction Technical Slice

The approved inventory and extraction implementation is a deterministic frontend mock workflow slice connected to the existing scan lifecycle. It keeps the public API endpoint set unchanged and adds only optional scan and metrics fields that tolerant clients may ignore.

Technical constraints:

- File inventory and content extraction are explicit workflow boundaries, not production source connectors.
- Inventory state is derived from controlled source metadata and sample-family fixtures.
- Extraction state reports method counts, warning counts, unsupported files, OCR-deferred files, and redacted evidence-candidate counts.
- Public payloads must not expose raw extracted text, full file content, page images, or unredacted personal data.
- Running scans may set partial metadata and warnings; completed scans must clear running partial warnings when all fixture stages are complete.
- The workflow must preserve deterministic reproducibility inputs, throughput, resource intensity, zero model calls, and zero estimated paid-service cost.
- Apache Tika and Tesseract are documented as future production candidates only; they are not added as runtime dependencies in this slice.
- Microsoft Graph delta query remains a future connector concept only; no production Graph integration is added.

## OpenRouter AI Assistive Processing Technical Slice

The approved AI implementation is a backend boundary for optional assistive classification of redacted, deterministic evidence. It is documented in `docs/design/openrouter-ai-processing.md`.

Technical constraints:

- Normal P0 full-scan, delta-scan, review, audit, metrics, and evaluation flows remain deterministic and report zero model calls unless a redacted AI classification path is explicitly invoked.
- AI calls require `DATASENTINEL_AI_MODE=assistive`, `OPENROUTER_API_KEY`, a configured model, and a passing budget preflight.
- The default model is `google/gemini-3.1-flash-lite` because current OpenRouter metadata shows no expiration, long context, and low-latency high-volume extraction positioning.
- The budget guard uses `DATASENTINEL_AI_BUDGET_EUR=25.00`, a conservative `DATASENTINEL_AI_BUDGET_USD=25.00`, and optional `OPENROUTER_USAGE_BASELINE_USD` from OpenRouter key usage.
- The AI path fails closed when OpenRouter usage cannot be checked and `DATASENTINEL_AI_FAIL_CLOSED=true`.
- Source/policy context, OCR, grep-style deterministic stages, and policy-pack context must run before AI escalation. OCR is local or deferred; it must not trigger paid AI by itself.
- External AI input must be redacted, anchored to deterministic evidence, and tied to active policy-pack context. Raw extracted text, file bodies, page images, credentials, tenant tokens, or unredacted personal data must not leave the process.
- AI output is Atlas stage-4 operational context support only. It must not provide legal advice, claim full GDPR compliance, assign owners, decide permissions, invent audit facts, or issue deletion instructions.
- Runtime AI metadata must map the tier plan to all 12 Atlas stages from source/policy context through evaluation metrics.

## Prelaunch Account System Technical Slice

The approved account implementation is a backend-owned Google/GitHub OAuth boundary documented in `docs/design/prelaunch-account-system.md`.

Technical constraints:

- Login uses provider authorization-code flow. GitHub login includes state and PKCE; Google login validates state and stable ID-token claims from the server exchange.
- Provider client secrets, provider access tokens, refresh tokens, auth transaction state, and PKCE verifier remain server-side and are never returned to React.
- The backend stores only local account profile and first-party session metadata.
- The browser session is represented by an HttpOnly first-party cookie.
- `/api/auth/providers`, `/api/auth/session`, and `/api/auth/logout` use the normal envelope shape; login and callback routes are redirects.
- `DATASENTINEL_AUTH_REQUIRED=true` protects workflow endpoints in prelaunch deployments. Development can keep it false for local contract testing.
- SQLite-backed prelaunch state uses the first-party session `userId` as the owner scope for Sources, scans, findings, audit events, metrics, and evaluation. Payload fields and compatibility headers must not override this owner scope.
- Legacy global SQLite source and workflow rows are quarantined outside authenticated account scopes during schema migration.
- Authentication does not change review permission boundaries, source connector permissions, deletion boundaries, or GDPR legal-advice constraints.

## Workspace Admin Permission Technical Slice

The approved Workspace implementation is a local P0 RBAC and invitation boundary documented in `docs/design/workspace-admin-permission-system.md`.

Technical constraints:

- Authentication creates or reads an account identity only; Workspace access requires active membership.
- `POST /api/workspaces` creates a local P0 Workspace and one active creator membership in `workspace_owner` and `workspace_admin`.
- `POST /api/workspaces/current` switches the current Workspace for an account that is already an active member of the target Workspace.
- SQLite-backed operational sources, scans, findings, audit events, metrics, and evaluation use the selected `workspace:{workspaceId}` owner scope when a current Workspace exists.
- Workspace groups carry explicit permissions from the exposed permission catalog and are evaluated with deny-by-default behavior.
- Workspace profile settings require `manage_workspace_settings`; the frontend profile editor exposes `name` and `description` as shell profile fields. Legacy `headerLabel` payload support remains compatibility-only and is not used as a visible sidebar property.
- The local API exposes Workspace directory, Workspace switch, admin summary, Workspace profile settings, owner-transfer, Workspace delete, group create/update/delete, member update/delete, invite-link generation, and invitation accept endpoints using the standard envelope and problem-details error format.
- Group deletion removes the group reference from memberships and pending invite links; the protected `workspace_owner` and `workspace_admin` groups cannot be deleted or stripped of required owner/admin-management permissions.
- Member updates and removals require `manage_workspace_members`, owner assignment changes require `manage_workspace_ownership`, and member changes cannot remove or demote the last active `workspace_owner` or `workspace_admin` member.
- Owner transfer assigns `workspace_owner` and `workspace_admin` to the target active member and removes `workspace_owner` from prior active owners; the frontend resolves the target from an exact active-member email match and requires a second confirmation before calling the API.
- Workspace deletion requires `manage_workspace_ownership` plus exact Workspace-name confirmation; the frontend also requires a second confirmation before the API soft-deletes the local Workspace, removes active memberships, revokes pending invitations, and clears affected current Workspace selections without deleting external source files.
- SQLite-backed deployments may persist local Workspace membership and invitation state, but this remains a prelaunch store and not production tenant authorization.
- The frontend Workspace menu, `/workspace/admin` overview, `/workspace/admin/members`, and `/workspace/admin/groups` routes consume contract data and tolerate no-Workspace, non-admin, empty, switched, and denied states.
- The frontend sidebar hides destinations outside the current Workspace permission boundary and marks expandable navigation groups with a chevron.
- Invitation acceptance must be idempotent at the membership level and must not create duplicate memberships.
- Workspace permissions do not enable production Microsoft Graph, enterprise directory sync, tenant provisioning, billing, source-file deletion, hidden permission data, legal advice, or full GDPR-compliance claims.

## Prelaunch Source Input Technical Slice

The approved source-input implementation is a prelaunch boundary for direct HTTPS file links and user-selected Google Drive files or folders. It is documented in `docs/design/google-drive-source-integration.md`.

Technical constraints:

- `remote_file_link` uses `config.url`, requires HTTPS, rejects embedded credentials, rejects private-address hosts, rejects Google Drive or Google Docs share pages, and supports only text-like content, PDF text layers, Office Open XML content, supported image files, supported transcript files, or recognized raw video media. Extractable files must stay within the prelaunch size limit; raw video media is reported as hard/OCR-deferred.
- `google_drive_selection` uses Google Picker in the browser to collect selected item metadata and Google Identity Services to obtain a short-lived access token for scan execution.
- The backend exposes `/api/integrations/google-drive/picker-config` for browser-safe Picker setup state behind the prelaunch session boundary; it must not expose client secrets or provider tokens.
- Google Drive scans receive `authorization.googleDriveAccessToken` only in the scan request and must not persist it; frontend status presentation may treat a Drive source as connected only while that token is present in browser memory.
- Source creation and Source metadata updates may set `assignedOwnerUserId` to an active Workspace member account ID; explicit null uses Data Steward fallback when available.
- Workspace Admin permission can edit Source ownership metadata, but business review visibility is still based on finding assignment rather than admin membership.
- The scanner reads source content into memory during scan execution and persists redacted evidence, finding, metric, and audit state only.
- Google Workspace documents may be exported to text-like content; folder traversal is bounded by the prelaunch file limit.
- PDF extraction is limited to existing text layers through the prelaunch document-reader boundary; OCR remains deferred.
- DOCX, XLSX, and PPTX extraction uses bounded stdlib ZIP/XML parsing, records recognition difficulty, and does not call OpenRouter by default.
- Source-registration deletion removes only DataSentinel metadata and must not mutate or delete source files in Google Drive, direct-link locations, or host-mounted roots.
- Production refresh-token storage, background Drive crawling, Microsoft Graph, tenant-wide source discovery, file upload storage, broad parser/OCR expansion beyond PDF text layers, and source-file deletion integrations are not added in this slice.

## Context and Risk Judgment Technical Slice

## Deterministic Signal Detection Technical Slice

The approved signal-detection implementation is a deterministic frontend mock workflow slice connected to the existing extraction lifecycle. It keeps the public API endpoint set unchanged and adds only optional scan, metrics, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Deterministic signal detection is an explicit workflow boundary after `extracting_content`; it is not context/risk judgment, owner routing, legal review, or deletion handling.
- The stage consumes internal extracted text/evidence candidates, detector rules version/hash, and active policy-pack evidence requirements.
- The stage exposes `signalDetection` as a scan summary with detector rules version/hash, evidence requirements, evaluated evidence-candidate count, detected/redacted signal count, findings-with-signals count, signal-type counts, warnings, and `rawContentExposed = false`.
- Public payloads must not expose raw extracted text, full file content, page images, detector secrets, raw source URLs, absolute source paths, adjacent unredacted match context, or unredacted personal data.
- The prelaunch detector set covers completed labeled form fields for names, dates of birth, employee/student/government identifiers, passport and driver-license fields, payment and bank data, online and device identifiers, location data, vehicle plates, access context, incident context, supplier tax IDs/addresses, health, biometric, genetic, race/ethnicity, political, religious, trade-union, sexual-orientation, criminal-record, family/minor, compensation, credential-secret, and free-text review comments in addition to email, phone, URL, handle, SSN/NINO, IP, MAC, UUID, coordinate, payment-card, and IBAN-like patterns.
- Evaluation must preserve a signal-detection rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Production NER, OCR, parser, Microsoft Graph, OAuth, directory, notification, ticketing, and deletion integrations are not added in this slice.

## Context and Risk Judgment Technical Slice

The approved context/risk implementation is a deterministic frontend mock workflow slice connected to the existing extraction and signal-detection lifecycle. It keeps the public API endpoint set unchanged and adds only optional scan, metrics, policy-pack, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Context/risk judgment is an explicit workflow boundary after `detecting_signals`; it is not owner routing, legal review, or deletion handling.
- The stage consumes redacted signal/evidence candidate counts, sample-family metadata, modified-time context, and active policy-pack guidance.
- The stage exposes `contextRisk` as a scan summary with policy-pack version, risk-rule fingerprint, context counts, risk counts, retention-review count, human-review count, warnings, and `legalConclusionProvided = false`.
- Missing policy guidance must produce neutral or unknown output instead of raw-content fallback or legal conclusions.
- Dashboard presentation must keep raw source text, file bodies, page images, unredacted personal data, and legal advice out of the UI.
- Evaluation must preserve a context-risk rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Microsoft Presidio is documented as a future production candidate only; it is not added as a runtime dependency in this slice.

## Owner Routing and Assignment Technical Slice

The approved owner-routing implementation is a deterministic frontend mock workflow slice connected to the existing context/risk lifecycle. It keeps the public API endpoint set unchanged and adds only optional scan, metrics, audit, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Owner routing is an explicit workflow boundary after `judging_context_risk`; it is not review support, human review, notification delivery, identity sync, or deletion handling.
- The stage consumes context/risk human-review counts, source Master of Data metadata, active policy-pack escalation paths, and organization-model routing strategy.
- The stage exposes `ownerAssignment` as a scan summary with policy-pack version, organization-model version, owner-resolution strategy, assignment-rule fingerprint, routed counts, escalation counts, and `unownedFindings = 0` for the controlled P0 fixture.
- Missing owner metadata must produce fallback, escalation, warning, or problem details instead of raw-content inspection or hidden failure.
- Dashboard presentation must keep raw source text, file bodies, page images, unredacted personal data, directory credentials, and legal advice out of the UI.
- Evaluation must preserve an owner-assignment rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Production Microsoft Graph, OAuth, directory, notification, ticketing, and deletion integrations are not added in this slice.

## Finding Assembly and Evidence Card Technical Slice

The approved finding-assembly implementation is a deterministic frontend mock workflow slice connected to the existing owner-routing lifecycle. It keeps the public API endpoint set unchanged and adds only optional scan, finding-row, metrics, audit, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Finding assembly is an explicit workflow boundary after `assigning_owner`; it is not review support, human review, production extraction, notification delivery, or deletion handling.
- The stage consumes redacted signal templates, context/risk counts, source snapshot identity, owner routing output, active policy-pack guidance, and audit context.
- The stage exposes `findingAssembly` as a scan summary with policy-pack version, source snapshot, assembly-rule fingerprint, assembled finding count, evidence-card count, evidence-signal count, missing-card count, denied-action count, redaction boundary, no-legal-conclusion boundary, and warnings.
- Completed scan state must update finding rows, finding detail records, metrics, audit events, and evaluation together so evidence cards are not disconnected from scan output.
- Evidence-card presentation must keep raw source text, file bodies, page images, unredacted personal data, legal advice, and deletion execution out of the UI.
- Evaluation must preserve a finding-assembly rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Production PII detection or anonymization tools such as Microsoft Presidio are documented as future candidates only; they are not added as runtime dependencies in this slice.

## Review Support and Permission Boundary Technical Slice

The approved review-support implementation is a deterministic frontend mock workflow slice connected to the existing finding-assembly lifecycle. It keeps the public API endpoint set unchanged and adds only optional scan, metrics, permission, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Review support is an explicit workflow boundary after `assembling_findings`; it is not durable authorization, identity sync, notification delivery, human review persistence, or deletion handling.
- The stage consumes assembled findings, owner assignment, active policy-pack decisions, active Workspace members when available, and actor permission boundary.
- The stage exposes `reviewSupport` as a scan summary with policy-pack version, organization-model version, support-rule fingerprint, supported finding count, available decision count, required reason count, checklist count, transfer count, escalation count, denied action count, redaction boundary, no-legal-conclusion boundary, and warnings.
- Finding-specific support exposes allowed decisions, denied actions, denial reasons, checklist items, transfer options from active Workspace members, and escalation options before submit. In Workspace context, clients must treat an empty Workspace transfer-target list as empty and must not refill it from static governance delegation fixtures.
- Review input validation rejects denied decisions, missing reasons, missing transfer targets, and missing escalation targets before changing finding, audit, source, metric, or evaluation state.
- Dashboard and finding detail presentation must keep raw source text, file bodies, page images, unredacted personal data, hidden permission data, legal advice, and deletion execution out of the UI.
- Evaluation must preserve a review-support rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Production authentication, authorization providers, Microsoft Graph, OAuth, directory, notification, ticketing, and deletion integrations are not added in this slice.

## Human Review Decision Handling Technical Slice

The approved human-review implementation is a deterministic frontend mock workflow slice connected to the existing review-support boundary. It keeps the public API endpoint set unchanged and adds only optional review, metrics, audit, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Human review command handling is an explicit workflow boundary after `preparing_review_support`; it is not real deletion, retention-label execution, production authorization, notification delivery, or durable backend persistence.
- The stage consumes the assembled finding, current review support, actor permission boundary, active policy-pack version, Workspace-member transfer targets, support-rule fingerprint, and review command input.
- The stage validates available decision, actor, reason, checklist acknowledgement, retention review date for retain decisions, transfer target, escalation queue, and idempotency before changing any state.
- Accepted decisions update finding status, delegated owner when applicable, audit timeline, review outcome metrics, backlog metrics, and evaluation traceability together.
- Accepted retain decisions update the finding retention state to `retained_until_review` in both list and detail payloads so a retained finding is not still presented as needing retention review.
- Rejected decisions must keep finding, source, audit, metric, and evaluation state unchanged.
- `delete_candidate` requires an explicit confirmation checklist item and is a status and audit outcome only; no source file, connector, retention label, deletion service, or external system is changed in P0.
- Dashboard and finding detail presentation must keep raw source text, file bodies, page images, unredacted personal data, hidden permission data, legal advice, and deletion execution out of the UI.
- Evaluation must preserve a human-review decision rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Production workflow engines, databases, ticketing systems, authorization providers, Microsoft Graph, OAuth, directory, notification, and deletion integrations are not added in this slice.

## Audit Event Recording Technical Slice

The approved audit-event implementation is a deterministic frontend mock workflow slice connected to the existing scan, owner-routing, finding-assembly, review-support, and human-review boundaries. It keeps the public API endpoint set unchanged and adds only optional audit, scan, metrics, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Audit recording is an explicit workflow boundary after `preparing_review_support`; it is not durable backend persistence, SIEM export, deletion execution, notification delivery, or production log management.
- The stage consumes scan lifecycle events, owner assignment, finding assembly, finding-level audit timelines, human-review decisions, active policy-pack version, permission boundary, review-support fingerprint, and idempotency context.
- Audit events expose actor type, object type, action, outcome, stage, previous state, resulting state, evidence references, redaction boundary, no-legal-conclusion boundary, and no-deletion boundary when available.
- The scan summary exposes `auditRecording` with policy-pack version, audit-rule fingerprint, event counts, linked finding count, review-decision count, human/system counts, and safety boundary booleans.
- Human-entered audit reason text must be sanitized for obvious emails, IBAN-like values, long numbers, and control characters before public display.
- Rejected or duplicate review commands must not create duplicate audit events or metric increments.
- Dashboard and audit presentation must keep raw source text, file bodies, page images, unredacted personal data, hidden permission data, legal advice, and deletion execution out of the UI.
- Evaluation must preserve an audit-recording rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Production event stores, SIEM pipelines, WORM storage, cryptographic signing, authorization providers, Microsoft Graph, OAuth, directory, notification, ticketing, and deletion integrations are not added in this slice.

## Incremental Delta Scan Technical Slice

The approved incremental delta implementation is a deterministic frontend mock workflow slice connected to the completed full-scan baseline. It keeps the public API endpoint set unchanged and adds only optional scan, metrics, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Delta scan is an explicit workflow boundary after audit recording and before later evaluation reporting; it is not a production connector or deletion mechanism.
- The stage requires a completed selected-source baseline and rejects missing, running, not-ready, or mismatched baselines before changing state.
- The stage exposes `deltaScan` as a scan summary with baseline scan ID, source snapshot, inventory fingerprint, baseline totals, delta fingerprint, changed/new/modified/unchanged/missing counts, carried-forward counts, reopened finding counts, warnings, and safety-boundary booleans.
- The pipeline may expose `comparing_delta_baseline` before changed-file inventory and extraction.
- Completed changed findings still flow through context/risk, owner routing, finding assembly, review support, audit recording, metrics, and evaluation.
- Missing files are represented as source inventory changes only; `deletionExecuted` and `missingFilesTreatedAsDeleted` remain `false`.
- Dashboard and Sources presentation must keep raw source text, file bodies, page images, unredacted personal data, hidden permission data, legal advice, and deletion execution out of the UI.
- Evaluation must preserve a delta rules hash, deterministic reproducibility, throughput, zero model calls, and zero estimated paid-service cost.
- Microsoft Graph delta query is documented as a future connector candidate only; no production Graph, OAuth, tenant, webhook, token storage, parser, OCR, AI, queue, database, ticketing, notification, retention-label, or deletion integration is added.

## Admin Metrics Aggregation Technical Slice

The approved admin-metrics implementation is a deterministic frontend mock workflow slice connected to full scan, delta scan, review support, human review decisions, audit recording, and evaluation. It keeps the public endpoint set unchanged and adds only optional metrics and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Admin metrics aggregation is an explicit workflow boundary after audit recording and before evaluation reporting; it is not a production analytics store, BI layer, legal reporting system, or deletion executor.
- The stage consumes scan coverage, inventory, extraction, context/risk, owner assignment, finding assembly, review support, audit recording, delta, human review, and evaluation summaries.
- The stage exposes an optional `AdminMetrics.aggregation` summary with status, input-stage basis, scan coverage, risk queue, owner backlog, review outcomes, audit evidence, delta counts, evaluation linkage, resource cost, and safety-boundary booleans.
- Running scans must set aggregation status to partial and carry upstream warnings.
- Completed scans must preserve the admin-metrics rules fingerprint in evaluation as `adminMetricsRulesHash`.
- Accepted review decisions update outcome, backlog, throughput, audit, and evaluation-linked aggregation exactly once; rejected and duplicate commands must not create duplicate metric increments.
- Dashboard presentation must keep raw source text, file bodies, page images, unredacted personal data, hidden permission data, legal advice, and deletion execution out of the UI.
- The implementation uses existing React, TypeScript, and Vitest only; no database, queue, analytics service, Microsoft Graph, OAuth, Purview, OCR, AI, or paid dependency is added.

## Evaluation Metrics Generation Technical Slice

The approved evaluation implementation is a deterministic frontend mock workflow slice connected to full scan, delta scan, admin metrics, human review decisions, and audit recording. It keeps the public endpoint set unchanged and adds only optional evaluation fields that tolerant clients may ignore.

Technical constraints:

- Evaluation generation is an explicit workflow boundary after admin metrics aggregation; it is not a production ML experiment tracker, BI store, legal report, or deletion proof.
- The stage consumes inventory, extraction, context/risk, owner assignment, finding assembly, review support, audit recording, delta, admin metrics, human-review outcome, and scan timing summaries.
- The stage exposes optional evaluation quality basis with golden dataset identity, input-stage basis, confusion matrix, scenario metrics, review throughput, risk-progress fields, safety boundaries, warnings, and an evaluation-rules fingerprint.
- Completed scans must compute precision, recall, F1, reproducibility, throughput, and resource-intensity fields from deterministic P0 formulas rather than disconnected constants.
- Accepted review decisions refresh review-throughput and risk-progress evaluation context exactly once; rejected and duplicate commands must not change evaluation state.
- Completed delta scans must evaluate changed files and preserve baseline, carried-forward, missing-file, no-raw-content, no-legal-conclusion, no-deletion, zero-model-call, and zero-cost boundaries.
- The Evaluation page must keep raw source text, file bodies, page images, unredacted personal data, hidden permission data, legal advice, and deletion execution out of the UI.
- The implementation uses existing React, TypeScript, and Vitest only; no scikit-learn, MLflow, database, queue, analytics service, Microsoft Graph, OAuth, Purview, OCR, AI, or paid dependency is added in P0.

## Remote Preview Deployment Technical Slice

The approved deployment implementation is a frontend preview plus loopback P0 API server on `agent-us`. Caddy serves the Vite build from `/srv/datasentinel/frontend/current` and reverse-proxies `/api/*` to the Python API server. It is documented in `docs/design/remote-preview-deployment.md`, `docs/design/agent-us-api-server-integration.md`, and `docs/DEPLOYMENT.md`.

Technical constraints:

- The preview serves only the Vite production build and uses browser-route fallback to `index.html`.
- The API server returns contract-compatible envelopes from existing mocks, in-memory scan/review state, or the approved local SQLite state file.
- The preview does not run a production database, queue, worker, OAuth flow, Microsoft Graph connector, tenant integration, production source connector, or deletion integration. If OpenRouter AI assistive mode is configured, it remains budget-guarded and redacted-evidence-only.
- The preview remains fixture-backed, in-memory, or local-SQLite-backed and must not expose raw sensitive values.
- Caddy configuration changes must be validated before reload and must have a rollback path through a saved Caddyfile backup and release symlink.
- Remote validation must check `/`, at least one internal route such as `/dashboard`, and `/api/health`.

## Agent-us API Server Technical Slice

The approved first server integration is a stdlib Python HTTP server with no added runtime dependency. It exposes the P0 OpenAPI paths, returns `data`/`meta` envelopes, uses `application/problem+json` for rejected commands, and keeps scan/review mutations in memory unless a local SQLite database path is configured.

Technical constraints:

- The frontend calls `/api` first and falls back to local mock workflow only when the server is unavailable; `application/problem+json` command rejections remain server responses and must not trigger mock scanning.
- Vite proxies `/api` to `127.0.0.1:8000` in development.
- Caddy proxies `/api/*` to the loopback API process on `agent-us`.
- `--db-path` or `DATASENTINEL_DB_PATH` may point the API server to a local SQLite file for restart-safe P0 state.
- Source connection checks may validate controlled mock and local demo sources but must not call production Microsoft Graph or external tenant APIs.
- Scan and review commands must preserve no-raw-content, no-legal-conclusion, and no-real-deletion boundaries.
- Python `http.server` is accepted only for this controlled P0 preview because official docs identify it as a basic server not recommended for production.
- Python `sqlite3` is accepted only as local P0 state tooling because official SQLite guidance supports local application storage, demo/testing use, and replacement of ad hoc disk files.

## Contract Baseline

- Base path: `/api`.
- Envelope: `data`, `meta`, and optional `pagination`.
- Error format: `application/problem+json`.
- State machines: scan, finding review, and contract lifecycle are documented in `docs/API_CONTRACT.md` and `docs/design/frontend-backend-delivery-contract.md`.
- Mocks are contract fixtures, not production seed data.
- Governance configuration is documented in `docs/GOVERNANCE_CONFIG.md`.
- Adaptive policy and review state machines are documented in `docs/design/adaptive-governance-review-control.md`.

## External Research Required Before Implementation

Official or authoritative documentation must be reviewed before integrating:

- Microsoft Graph or any file-source API.
- GDPR deletion, retention, or audit-related workflow assumptions.
- The organizer sample repository before downloading or vendoring sample files.
- Any AI, OCR, document parsing, or classification dependency.
- Any production storage, authentication, authorization, or deployment platform beyond the approved local SQLite P0 state file.

## Technical Done When

The first implementation task has:

- A narrow acceptance criterion.
- A documented impact surface.
- A state machine if it introduces workflow, permissions, asynchronous work, or external protocols.
- Targeted validation commands.
