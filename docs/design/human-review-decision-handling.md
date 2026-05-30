# Human Review Decision Handling

## Problem Definition

After review support is prepared, DataSentinel needs to accept a human review decision as an accountable workflow command. The command must connect the assembled evidence card, owner assignment, active policy pack, review-support checklist, actor permission boundary, audit trail, metrics, and evaluation data without executing real deletion or turning policy guidance into legal advice.

The repository Atlas reference in `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md` frames DataSentinel as a responsible deletion control tower: AI and deterministic rules provide evidence, while humans remain accountable for final decisions. This slice implements that boundary for P0 mock workflows.

## Scope

Included:

- Deterministic command handling for `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate`.
- Validation against current finding-specific review support and permission boundary.
- Required human reason, required checklist acknowledgement, required retention review date for retain decisions, required transfer target, and required escalation queue.
- Idempotent duplicate handling for repeated review submissions when a command key is available.
- Finding status, owner assignment, audit event, metrics, and evaluation updates in one explicit state transition.
- Visible no-deletion boundary for `delete_candidate`.

Excluded:

- Real source-file deletion, redaction execution, retention-label writes, ticketing, notification delivery, identity sync, production authorization, Microsoft Graph, OAuth, tenant, database, queue, model, OCR, or paid-service integration.
- Legal conclusions, legal advice, or claims of full GDPR compliance.
- Automatic retention, deletion, masking, or access restriction.

## Research Basis

- The European Commission describes accountability as the organization being responsible for complying with data-protection principles and demonstrating compliance: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/obligations/how-can-i-demonstrate-my-organisation-compliant-gdpr_en
- The European Commission GDPR principles overview supports data minimisation, storage limitation, integrity/confidentiality, and accountability as operating constraints: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en
- The European Commission right-to-erasure guidance records that erasure is not absolute when legal obligations or other exceptions apply, so P0 must create delete candidates rather than execute deletion: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/dealing-citizens/do-we-always-have-delete-personal-data-if-person-asks_en
- EUR-Lex Regulation (EU) 2016/679 is the official GDPR text and is the basis for Article 17 and Article 30 record-keeping references: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- EDPB DPIA guidance treats high-risk processing as structured assessment work, which supports escalation and human-accountable review instead of automated legal decisions: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/data-protection-impact-assessments-high-risk-processing_en

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| HREV-REQ-001 | Treat review decisions as accountable human commands; AI, detectors, and policy guidance do not own the legal or business decision. |
| HREV-REQ-002 | Accept decisions only after evidence card, owner routing, review support, active policy pack, and actor permission boundary are available. |
| HREV-REQ-003 | Represent deletion as `delete_candidate` in P0; do not mutate source files, execute deletion, or imply deletion approval. |
| HREV-REQ-004 | `keep_with_reason` must preserve a human reason and a future retention review date so retention is not silent indefinite storage. |
| HREV-REQ-005 | `correct_false_positive` must preserve human feedback for evaluation and future detector review without changing detector code. |
| HREV-REQ-006 | `reassign_owner` and `escalate` must preserve target owner or queue context for accountability and SLA follow-up. |
| HREV-REQ-007 | Every accepted decision must create an audit event with actor, timestamp, finding, decision, reason, resulting status, policy-pack version, permission-boundary fingerprint, and review-support rules fingerprint when known. |
| HREV-REQ-008 | Denied decisions, missing reasons, missing checklist acknowledgements, missing retention review dates, missing targets, stale support, and repeated commands must not create duplicate or partial state changes. |
| HREV-REQ-009 | Public payloads and UI state must not expose raw source content, unredacted personal data, credentials, hidden permission data, or legal conclusions. |
| HREV-REQ-010 | Metrics and evaluation must expose review outcomes, backlog movement, deterministic reproducibility, zero model calls, and zero estimated paid-service cost. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Keep review handling inline in the UI provider | Fast | Hides command validation and makes tests depend on React state | Rejected |
| Add a pure human-review command module | Testable, reversible, keeps side effects at the provider boundary | Requires a small internal result type | Accepted |
| Persist decisions in a backend database now | Closer to production | Out of P0 scope and introduces storage/security decisions too early | Rejected |
| Add a workflow engine | Strong future audit semantics | Too expensive and unnecessary for fixture-backed P0 | Rejected |
| Use existing OpenAPI + deterministic Vitest state-machine tests | Contract-first, cheap, reproducible | Does not provide durable production persistence | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Review supported | Submit decision | Decision is in `availableDecisions`, actor matches support, checklist complete, reason exists, support is current | Decision accepted | Build review record and audit event |
| Review supported | Submit delete candidate | Real deletion remains denied | Delete candidate | Set finding status to `delete_candidate`; no source mutation |
| Review supported | Submit retain | Retention review date exists | Retained | Set finding status to `retained`; record retention review date |
| Review supported | Submit false positive | Human reason exists | False positive | Set finding status to `false_positive`; record feedback for evaluation |
| Review supported | Submit transfer | Transfer target exists in support | Assigned | Set owner to delegated target and keep review task open |
| Review supported | Submit escalation | Escalation queue exists in support | Escalated | Set finding status to `escalated`; record queue target |
| Review supported | Submit denied or incomplete command | Guard fails | Review supported | Return validation reason; no finding, source, audit, metric, or evaluation change |
| Review supported | Submit duplicate command | Idempotency key already recorded for same finding | Decision already accepted | Return existing audit context; no duplicate audit event or metric change |
| Review supported | Policy or permission support changed | Fingerprint mismatch is detected | Review support stale | Recalculate support before accepting a new command |

## Failure Paths

- Unknown finding: reject the command and keep all state unchanged.
- Actor mismatch: reject because the command is not tied to the visible permission boundary.
- Decision outside `availableDecisions`: reject and keep all state unchanged.
- Missing reason: reject and keep all state unchanged.
- Missing required checklist acknowledgement: reject and keep all state unchanged.
- Missing retention review date for `keep_with_reason`: reject and keep all state unchanged.
- Missing or unknown transfer target: reject and keep all state unchanged.
- Missing or unknown escalation queue: reject and keep all state unchanged.
- Duplicate idempotency key: return idempotent success without duplicate audit, metrics, source, or finding changes.
- Delete candidate: never changes source-file, deletion, or connector state in P0.

## Public Contract Strategy

The endpoint set stays unchanged. `POST /api/findings/{findingId}/review` may include optional fields already aligned with the tolerant contract:

- `retentionUntil` for retain decisions.
- `checklistItemIds` for required review-support checklist acknowledgement.

The response may include optional fields:

- `targetId`, `targetLabel`, `retentionUntil`, `idempotencyKey`, `policyPackVersion`, `permissionBoundaryFingerprint`, `reviewSupportRulesFingerprint`, and `deletionExecuted = false`.

Metrics and evaluation may include optional human-review decision counters and hashes. Required fields remain stable inside contract version `0.1.0`.

## Impact Surface

- `docs/API_CONTRACT.md`, `contracts/schemas/finding-review.yaml`, `contracts/schemas/metrics.yaml`, and mock payloads gain optional human-review decision fields.
- `frontend/src/data` gains a pure decision-handling module and focused behavior tests.
- `frontend/src/data/DataProvider.tsx` delegates review updates to the module.
- `frontend/src/pages/FindingDetailPage.tsx` passes checklist acknowledgement and retention review date from the Review Dialog.
- `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, and `ACCEPTANCE.md` gain the current slice requirements.

## Rollback Path

1. Remove the human-review decision module and restore inline provider review handling.
2. Remove optional `checklistItemIds`, optional response metadata, and optional metrics/evaluation fields.
3. Keep existing `POST /api/findings/{findingId}/review` endpoint and required fields unchanged.
4. Keep audit events for accepted decisions, because that is already part of P0 product acceptance.

This rollback does not require a contract version bump because required fields and endpoint paths remain unchanged.

## Primitive Acceptance Criteria

- A review decision cannot be accepted until current finding-specific review support supplies the available decision and permission boundary.
- An accepted decision records one review record and one audit event with human actor, timestamp, reason, decision, resulting status, policy-pack version, and permission context.
- `delete_candidate` changes only finding review status and audit state; it never mutates source files or executes deletion.
- `keep_with_reason` requires and records a retention review date.
- `reassign_owner` requires and records a supported target owner.
- `escalate` requires and records a supported escalation queue.
- Missing reason, missing checklist acknowledgement, missing retention review date, denied actor, denied decision, missing transfer target, and missing escalation queue reject before any state change.
- Duplicate idempotency keys do not create duplicate audit events or metric increments.
- Admin metrics expose review decision totals, outcome counts, backlog movement, and review throughput inputs when available.
- Evaluation preserves human-review decision rules traceability while keeping model calls and estimated paid-service cost at zero.
