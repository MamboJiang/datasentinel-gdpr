# Audit Event Recording

## Problem Definition

After human review command handling, DataSentinel needs audit events to become a first-class lifecycle record rather than a few static rows. The audit trail must connect scan start, scan completion, owner assignment, finding assembly, finding-level timeline events, and human review decisions into one structured trace that can be shown in the audit view, finding detail timeline, metrics, and evaluation output.

The repository Atlas reference in `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md` frames DataSentinel as a responsible deletion control tower. It explicitly treats `AuditEvent` as a first-class object and defines the minimum audit shape as actor, action, object, timestamp, before/after context, and evidence. This slice implements that requirement for the P0 fixture-backed workflow without adding durable backend storage or production integrations.

## Scope

Included:

- A shared audit-event creation boundary for scan, owner-assignment, finding-assembly, finding timeline, and human-review events.
- Structured audit fields for actor type, object type, action, outcome, stage, previous state, resulting state, evidence references, policy-pack version, permission fingerprint, review-support fingerprint, and no-deletion boundary.
- Audit-recording scan summary and pipeline stage after review support.
- Metrics and evaluation traceability for audit-event recording.
- Sanitization for human-entered audit text so obvious emails, IBAN-like values, long numbers, and control characters are not stored in public audit payloads.
- Behavior tests for connected lifecycle events, finding timeline inclusion, review-event idempotency continuity, redaction, and no-real-deletion state.

Excluded:

- Production database, append-only event store, SIEM export, object-lock storage, cryptographic signing, WORM retention, queue, notification, Microsoft Graph, OAuth, tenant, AI, OCR, model, ticketing, deletion, retention-label, or access-change integration.
- Legal advice, legal conclusions, or claims of full GDPR compliance.
- Automatic deletion, automatic access restriction, or source-file mutation.

## Research Basis

- EUR-Lex Regulation (EU) 2016/679 Article 5(2) makes the controller responsible for and able to demonstrate compliance with the processing principles. Article 30 describes written records of processing activities, including purposes, categories, recipients, erasure timing where possible, and security measures. Article 32 requires security appropriate to risk, cost, state of the art, and processing context: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- OWASP Logging Cheat Sheet recommends application-level logging for security and audit trails, recording when/where/who/what, avoiding over-logging, excluding or masking sensitive personal data, and protecting logs from tampering and unauthorized access: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- NIST SP 800-92 provides authoritative guidance for enterprise log management practices and audit/accountability control families. P0 applies the shape and process discipline without introducing a production log-management stack: https://csrc.nist.gov/pubs/sp/800/92/final
- Microsoft OneDrive/SharePoint scan guidance says delta query supports initial crawl plus future change tracking and helps reduce repeated enumeration cost. This remains a future connector concern; P0 records audit events for full-scan and review lifecycle only: https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/scan-guidance

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| AUDIT-REQ-001 | Treat `AuditEvent` as a first-class object, not a UI-only decoration. |
| AUDIT-REQ-002 | Record actor, action, object, timestamp, before/after state, and evidence references for visible lifecycle changes. |
| AUDIT-REQ-003 | Connect audit events across discovery, classification continuity, owner routing, finding evidence cards, human review, deletion-candidate decisions, and delta-readiness. |
| AUDIT-REQ-004 | Keep AI and deterministic rules as evidence providers while humans remain accountable for review decisions. |
| AUDIT-REQ-005 | Preserve policy-pack version, permission boundary, review-support fingerprint, owner or escalation target, and idempotency context where available. |
| AUDIT-REQ-006 | Never expose raw source content, unredacted personal data, credentials, hidden permission data, or legal conclusions in audit payloads. |
| AUDIT-REQ-007 | Represent deletion as an auditable candidate state in P0; do not execute deletion, retention-label writes, or access changes. |
| AUDIT-REQ-008 | Keep the P0 implementation deterministic, reproducible, zero-model-call, and zero-paid-service for affordability. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Keep event construction spread across workflow modules | Fast | Inconsistent shape and weak sanitization | Rejected |
| Add a small shared audit-event creation module | Consistent, testable, low-cost, reversible | Still not durable production persistence | Accepted |
| Add a workflow engine or event-sourcing framework | Strong long-term audit semantics | Too expensive and out of P0 scope | Rejected |
| Add a SIEM/export dependency now | Enterprise-like | Requires storage, security, retention, and deployment decisions outside this slice | Rejected |
| Use optional OpenAPI fields and fixture-backed Vitest tests | Contract-first and affordable | Does not prove production tamper resistance | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Source ready | Full scan started | Source is P0 scan-ready | Audit recording pending | Record `full_scan_started` with source and policy references |
| Scan running | Full scan completed | Scan ID matches running scan | Audit recording completed | Record scan completion, owner assignment, finding assembly, and finding timeline events |
| Finding assembled | Owner assigned | Owner routing produced direct, fallback, or escalation owner | Finding assigned | Record finding-level assignment event |
| Review support ready | Human decision accepted | Decision, actor, checklist, reason, and target guards pass | Review recorded | Record one review audit event and update audit summary counts |
| Review support ready | Human decision rejected | Guard fails | Review support ready | No audit, finding, source, metric, or evaluation change |
| Decision already recorded | Duplicate idempotency key received | Existing event has same finding and idempotency key | Decision already recorded | Return existing audit context without duplicate event |

## Failure Paths

- Not-ready source: do not create scan or audit state.
- Scan completion mismatch: keep state unchanged.
- Missing finding: reject review command without audit state changes.
- Denied actor, denied decision, missing reason, missing checklist, missing retention date, missing transfer target, missing escalation queue, or stale review support: reject before audit state changes.
- Human-entered reason contains obvious sensitive values: mask them before storing the public audit event.
- Duplicate idempotency key: return the existing audit event without changing metrics or audit counts.
- Delete candidate: record `deletionExecuted = false`; no source-file, connector, retention-label, access-control, or deletion service mutation occurs.

## Public Contract Strategy

The endpoint set remains unchanged. `GET /api/audit/events` and finding detail `auditTimeline` may include optional fields:

- `actorType`, `recordedAt`, `auditRecordVersion`, `objectType`, `objectId`, `action`, `outcome`, `stage`, `sourceId`, `previousState`, `resultingState`, `evidenceReferences`, `rawContentExposed`, and `legalConclusionProvided`.

`GET /api/scans/{scanId}` may include optional `auditRecording`. Admin metrics and evaluation may include optional audit counts and `auditRecordingRulesHash`.

Required fields remain stable inside contract version `0.1.0`, and clients must continue to ignore unknown fields.

## Impact Surface

- `contracts/schemas/finding-review.yaml`, `contracts/schemas/source-scan.yaml`, `contracts/schemas/metrics.yaml`, and mock fixtures gain optional audit fields.
- `frontend/src/data/auditEventRecording.ts` centralizes audit event creation, sanitization, event prepending, timeline collection, and audit summary calculation.
- Existing scan and review workflow modules route event creation through the shared boundary.
- The Dashboard pipeline and Audit page expose audit-recording status without showing raw content or legal conclusions.
- `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, `docs/API_CONTRACT.md`, and `ACCEPTANCE.md` gain this slice.

## Rollback Path

1. Remove `scan.auditRecording`, audit metrics, and `auditRecordingRulesHash`.
2. Keep required `AuditEvent` fields and existing `/api/audit/events` endpoint unchanged.
3. Revert workflow event creation to the previous scan/review helper functions.
4. Keep review decision audit events because they are already part of P0 acceptance.

This rollback does not require a contract version bump because only optional fields are added.

## Primitive Acceptance Criteria

- A completed scan exposes `recording_audit_events` after `preparing_review_support`.
- Scan start, scan completion, owner assignment, finding assembly, finding assembled, finding assigned, and accepted review decisions are all structured audit events with actor, action, object, timestamp, state transition, and evidence references.
- Completed scan audit summary exposes recorded event count, scan-linked count, finding-linked count, review-decision count, human/system counts, `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false`.
- Accepted review decisions update the finding timeline, global audit list, audit summary, audit metrics, and evaluation traceability together.
- Denied, incomplete, stale, unknown, or duplicate review commands do not create duplicate audit events or metric increments.
- Human-entered audit text is sanitized for obvious emails, IBAN-like values, long numbers, and control characters before it appears in public audit payloads.
- The implementation remains deterministic, zero-model-call, zero-estimated-paid-service-cost, and free of production storage, connector, authorization, and deletion integrations.
