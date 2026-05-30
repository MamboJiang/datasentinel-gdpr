# Technical Requirements Document

## Current Technical Scope

This repository is initialized for documentation, collaboration, contract-first parallel delivery, and a controlled remote frontend preview. The approved technical baseline is the tolerant REST contract in `contracts/openapi.yaml`, its split schemas in `contracts/schemas/`, mock fixtures in `contracts/mocks/`, and the static frontend preview documented in `docs/DEPLOYMENT.md`.

No backend runtime, database, queue, external API integration, authentication, authorization, production file-source connection, or deletion-capable deployment path is approved yet.

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

## Context and Risk Judgment Technical Slice

The approved context/risk implementation is a deterministic frontend mock workflow slice connected to the existing extraction and signal-detection lifecycle. It keeps the public API endpoint set unchanged and adds only optional scan, metrics, policy-pack, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Context/risk judgment is an explicit workflow boundary after `detecting_signals`; it is not owner routing, legal review, or deletion handling.
- The stage consumes redacted evidence candidate counts, sample-family metadata, and active policy-pack guidance.
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
- The stage consumes assembled findings, owner assignment, active policy-pack decisions, organization-model delegation targets, and actor permission boundary.
- The stage exposes `reviewSupport` as a scan summary with policy-pack version, organization-model version, support-rule fingerprint, supported finding count, available decision count, required reason count, checklist count, transfer count, escalation count, denied action count, redaction boundary, no-legal-conclusion boundary, and warnings.
- Finding-specific support exposes allowed decisions, denied actions, denial reasons, checklist items, transfer options, and escalation options before submit.
- Review input validation rejects denied decisions, missing reasons, missing transfer targets, and missing escalation targets before changing finding, audit, source, metric, or evaluation state.
- Dashboard and finding detail presentation must keep raw source text, file bodies, page images, unredacted personal data, hidden permission data, legal advice, and deletion execution out of the UI.
- Evaluation must preserve a review-support rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Production authentication, authorization providers, Microsoft Graph, OAuth, directory, notification, ticketing, and deletion integrations are not added in this slice.

## Human Review Decision Handling Technical Slice

The approved human-review implementation is a deterministic frontend mock workflow slice connected to the existing review-support boundary. It keeps the public API endpoint set unchanged and adds only optional review, metrics, audit, and evaluation fields that tolerant clients may ignore.

Technical constraints:

- Human review command handling is an explicit workflow boundary after `preparing_review_support`; it is not real deletion, retention-label execution, production authorization, notification delivery, or durable backend persistence.
- The stage consumes the assembled finding, current review support, actor permission boundary, active policy-pack version, organization-model transfer targets, support-rule fingerprint, and review command input.
- The stage validates available decision, actor, reason, checklist acknowledgement, retention review date for retain decisions, transfer target, escalation queue, and idempotency before changing any state.
- Accepted decisions update finding status, delegated owner when applicable, audit timeline, review outcome metrics, backlog metrics, and evaluation traceability together.
- Rejected decisions must keep finding, source, audit, metric, and evaluation state unchanged.
- `delete_candidate` is a status and audit outcome only; no source file, connector, retention label, deletion service, or external system is changed in P0.
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

## Remote Preview Deployment Technical Slice

The approved deployment implementation is a static frontend preview on `agent-us`, served by the existing Caddy service from `/srv/datasentinel/frontend/current`. It is documented in `docs/design/remote-preview-deployment.md` and `docs/DEPLOYMENT.md`.

Technical constraints:

- The preview serves only the Vite production build and uses browser-route fallback to `index.html`.
- The preview does not run a backend API, database, queue, worker, OAuth flow, Microsoft Graph connector, tenant integration, AI service, or deletion integration.
- The preview remains fixture-backed through existing contract mocks and must not expose raw sensitive values.
- Caddy configuration changes must be validated before reload and must have a rollback path through a saved Caddyfile backup and release symlink.
- Remote validation must check `/` and at least one internal route such as `/dashboard`.

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
- Any storage, authentication, authorization, or deployment platform.

## Technical Done When

The first implementation task has:

- A narrow acceptance criterion.
- A documented impact surface.
- A state machine if it introduces workflow, permissions, asynchronous work, or external protocols.
- Targeted validation commands.
