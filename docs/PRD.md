# Product Requirements Document

## Product Goal

Provide a prototype workflow that shows how an organization can discover GDPR-relevant data, classify risk, assign ownership, support human review, and prove the outcome.

## Initial User Journey

1. A privacy or IT user starts with a controlled sample file source.
2. The system identifies candidate files that may contain personal or GDPR-relevant data.
3. The system explains why each finding matters.
4. The system suggests an accountable owner or escalation path.
5. A human reviewer decides whether to delete, retain, mask, archive, or escalate the finding.
6. The system records the decision in an audit trail.
7. A later delta scan focuses only on new or changed files.

## Required Capabilities

- Full-scan concept for initial discovery.
- Classification concept for personal-data findings and risk context.
- Owner-routing concept for review accountability.
- Human-review concept with decision reasons.
- Audit-log concept for evidence and outcomes.
- Delta-scan concept for ongoing governance.
- Admin-reporting concept for scanned files, flagged files, scanned volume, progress, scan time, backlog, and risk distribution.
- Evaluation concept for accuracy, reproducibility, speed, and resource intensity.
- Governance-configuration concept for policy packs, organization model, permissions, review support, and change previews.
- User-control concept for visible allowed actions, denied actions, and reason requirements.

## Backend Planning Sequence After Sample Source Connection

Once a controlled sample source is connected, P0 delivery should proceed through a backend planning sequence rather than a broad scanner build:

1. Represent a full scan and its progress.
2. Inventory and extract file candidates without exposing raw sensitive text.
3. Detect deterministic evidence signals.
4. Classify context, risk, and retention status from evidence and policy guidance.
5. Route each finding to a direct owner, Master of Data fallback, or escalation path.
6. Assemble finding list and evidence-card data.
7. Expose review support and permission boundaries before review submission.
8. Record human review decisions with reasons.
9. Record audit events for visible workflow state changes.
10. Represent delta scans against a prior full-scan baseline.
11. Aggregate admin metrics.
12. Publish evaluation metrics.

The detailed planning notes are `docs/design/backend-post-source-execution-plan.md` and `docs/design/backend-post-source-stage-details.md`.

## Full Scan Start Implementation Slice

The first implementation slice for full scan start is a fixture-backed workflow that connects source readiness to scan status, metrics, audit, and evaluation surfaces. It must:

- Use the organizer sample source as the default P0 full-scan target.
- Pass an explicit `sourceId` when starting a scan.
- Allow full-scan start only for sources that are scan-ready in the P0 mock governance model.
- Record visible scan-start and scan-completion audit events.
- Update admin metrics while running and after completion.
- Keep evaluation deterministic and cost-free until a real scanner harness exists.
- Avoid raw source content, legal conclusions, production connectors, and real deletion.

## Source Inventory and Content Extraction Slice

The next implementation slice connects the running scan to observable file inventory and content extraction. It must:

- Build deterministic file-candidate counts from the selected controlled source.
- Preserve source snapshot and file fingerprint summary data for reproducibility and later delta scans.
- Summarize content extraction status, supported methods, warning counts, and redacted evidence-candidate counts.
- Show unsupported or OCR-deferred files as recoverable warnings.
- Keep raw extracted text, file bodies, page images, and unredacted personal data outside public payloads.
- Keep AI/model calls and estimated paid-service cost at zero for P0.
- Leave deterministic signal detection, risk scoring, owner routing, and review decisions in their existing downstream stages.

The detailed design note is `docs/design/source-inventory-content-extraction.md`.

## Context and Risk Judgment Slice

The next implementation slice connects extracted evidence candidates and deterministic signal detection to context/risk judgment. It must:

- Add a visible context/risk stage after signal detection and before scan completion.
- Use active policy-pack guidance, sample-family metadata, and redacted evidence candidate counts.
- Expose context, risk, retention-review, and human-review counts without raw source content.
- Attach the active policy-pack version and a risk-rule fingerprint for audit and evaluation.
- Keep legal conclusions out of product output by exposing `legalConclusionProvided = false`.
- Keep deterministic processing, model calls, and estimated paid-service cost at zero for P0.
- Leave owner routing, review support, and human review decisions in their downstream stages.

The detailed design note is `docs/design/context-risk-judgment.md`.

## Owner Routing and Assignment Slice

The next implementation slice connects context/risk judgment to accountable owner routing. It must:

- Add a visible owner-assignment stage after context/risk judgment and before scan completion.
- Use human-review counts, source Master of Data metadata, organization model, and policy-pack escalation paths.
- Route review-required findings to direct owners, Master of Data fallback, or escalation paths without leaving findings silently unowned.
- Attach policy-pack version, organization-model version, owner-resolution strategy, and assignment-rule fingerprint for audit and evaluation.
- Create an audit-visible owner-assignment event when review-required findings are routed.
- Keep legal conclusions, raw source content, production directory integrations, real deletion, model calls, and estimated paid-service cost out of P0.
- Leave review support and human review decisions in their downstream stages.

The detailed design note is `docs/design/owner-routing-assignment.md`.

## Finding Assembly and Evidence Card Slice

The next implementation slice connects owner routing to the findings table and evidence-card detail view. It must:

- Add a visible finding-assembly stage after owner assignment and before scan completion.
- Assemble finding rows and evidence-card details from redacted signals, context/risk output, owner assignment, active policy pack, source snapshot, and audit context.
- Ensure every assembled finding has at least one redacted evidence signal and one evidence card.
- Show policy context, owner routing, retention status, allowed actions, denied actions, and audit history without exposing raw source content.
- Attach policy-pack version, source snapshot, and assembly-rule fingerprint for audit and evaluation.
- Keep legal conclusions, raw source content, production parser integrations, real deletion, model calls, and estimated paid-service cost out of P0.
- Leave review support and human review command handling in their downstream stages.

The detailed design note is `docs/design/finding-assembly-evidence-card.md`.

## Review Support and Permission Boundary Slice

The next implementation slice connects evidence cards to human-review readiness. It must:

- Add a visible review-support preparation stage after finding assembly.
- Derive finding-specific support from assembled evidence cards, owner assignment, active policy pack, organization model, and actor permission boundary.
- Show allowed actions, denied actions, denial reasons, checklist items, transfer options, escalation options, and reason requirements before submission.
- Ensure delete candidate, keep with reason, false positive correction, reassign, and escalate decisions are visible when allowed by the boundary.
- Reject denied review attempts, missing reasons, missing transfer targets, and missing escalation targets without changing finding, source, metric, or audit state.
- Attach policy-pack version, organization-model version, permission-boundary fingerprint, and review-support rules fingerprint for audit and evaluation.
- Keep legal conclusions, raw source content, production authorization, real deletion, model calls, and estimated paid-service cost out of P0.
- Leave durable backend persistence and production authorization providers to future implementation.

The detailed design note is `docs/design/review-support-permission-boundary.md`.

## Human Review Decision Handling Slice

The next implementation slice connects review support to accountable outcomes. It must:

- Accept only decisions that are currently available to the actor through finding-specific review support.
- Record `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate` as human decisions with reasons.
- Require checklist acknowledgement before submit so reviewers do not bypass visible evidence, owner, retention, and permission context.
- Require `keep_with_reason` to include a retention review date.
- Require transfer and escalation decisions to include a supported owner or queue target.
- Create one review record and one audit event for every accepted decision.
- Keep real deletion represented only as a denied action; `delete_candidate` never mutates source files in P0.
- Update outcome metrics, review backlog, audit context, and evaluation traceability without model calls or paid services.

The detailed design note is `docs/design/human-review-decision-handling.md`.

## Audit Event Recording Slice

The next implementation slice connects previous workflow events into one accountable audit trail. It must:

- Treat audit events as first-class records for scan start, scan completion, owner assignment, finding assembly, finding-level timelines, and accepted human review decisions.
- Record actor, action, object, timestamp, previous state, resulting state, outcome, evidence references, policy-pack version, permission context, and review-support fingerprint where available.
- Expose an audit-recording pipeline stage and scan summary after review support.
- Update global audit list, finding audit timelines, admin audit metrics, and evaluation traceability together.
- Sanitize human-entered audit text before it appears in public payloads.
- Keep raw source content, unredacted personal data, hidden permission data, legal conclusions, deletion execution, production storage, production connector, and paid-service dependencies out of P0.

The detailed design note is `docs/design/audit-event-recording.md`.

## P0 Screens and API Consumers

- Public project homepage.
- Source connector view.
- Admin dashboard.
- Findings table.
- Evidence card.
- Review action panel.
- Audit timeline or report view.
- Evaluation tab.
- Governance settings inspection.
- Permission boundary view.

These surfaces must consume the tolerant contract defined in `docs/API_CONTRACT.md` and `contracts/openapi.yaml`.

## Explicitly Deferred

- Production Microsoft 365 integration.
- Real deletion of remote files.
- Authentication and authorization implementation.
- Persistent storage selection.
- AI model or vendor selection.
- User interface implementation.

## Product Constraints

- User-facing and repository text must be English.
- Deletion must be human-accountable.
- Sensitive snippets should be minimized or masked in any future UI.
- Frontend and backend work must use the shared API contract and mock fixtures.
- Legal rules must be represented as configurable guidance, not fixed code conclusions.
- User interfaces must show permission boundaries and avoid surprising denial after submit.
- Requirements changes must update this document and `ACCEPTANCE.md`.
