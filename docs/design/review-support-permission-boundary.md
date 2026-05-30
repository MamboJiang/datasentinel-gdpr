# Review Support and Permission Boundary

## Problem Definition

After finding assembly, DataSentinel needs to tell a human reviewer what they can do, what they cannot do, what evidence must be checked, and which policy-pack version governs the decision. This stage must connect the assembled finding, owner routing, active governance model, and actor permission boundary before any review command is submitted.

The separate local Atlas markdown referenced by the user was not present in this repository or the searched `/Users/y.h/Documents` directory at implementation time. This design therefore applies the Atlas-derived continuity requirements already recorded in `docs/design/source-inventory-content-extraction.md`, `docs/design/context-risk-judgment.md`, `docs/design/owner-routing-assignment.md`, and `docs/design/finding-assembly-evidence-card.md`, plus the adaptive governance contract.

## Scope

Included:

- Deterministic scan-level `reviewSupport` summary after finding assembly.
- Finding-specific reviewer support from assembled evidence cards, active policy pack, organization model, and actor permissions.
- Visible allowed actions, denied actions, denial reasons, checklists, reason requirements, transfer options, and escalation options.
- Permission-aware review input validation in the mock workflow.
- Metrics and evaluation traceability for the review-support rules hash.

Excluded:

- Production authentication, authorization, Microsoft Graph, OAuth, tenant, directory, notification, ticketing, deletion, AI, model, OCR, database, or queue integrations.
- Automatic deletion or source mutation.
- Legal advice, legal conclusions, or claims of full GDPR compliance.

## Research Basis

- European Commission GDPR principles overview records data minimisation, storage limitation, integrity/confidentiality, and accountability as core processing principles: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en
- European Commission accountability guidance says organizations are responsible for complying with data-protection principles and demonstrating compliance: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/obligations/how-can-i-demonstrate-my-organisation-compliant-gdpr_en
- EDPB DPIA guidance treats high-risk processing as structured risk assessment work; this stage therefore provides review support and audit context, not an automated legal conclusion: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/data-protection-impact-assessments-high-risk-processing_en
- EDPB 2026 DPIA template direction emphasizes structured, consistent evidence for DPIA work. P0 stays economically affordable by using deterministic fixtures, zero model calls, and zero paid services: https://www.edpb.europa.eu/news/news/2026/enhancing-compliance-and-consistency-edpb-adopts-dpia-template_hr

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| REVIEW-REQ-001 | Preserve continuity from source inventory, extraction, context/risk, owner routing, and finding assembly before preparing review support. |
| REVIEW-REQ-002 | Show permissions before action, including allowed actions, denied actions, and denial reasons. |
| REVIEW-REQ-003 | Require a human actor and reason for every review decision. |
| REVIEW-REQ-004 | Provide checklist, transfer, and escalation support from policy-pack and organization-model concepts instead of hard-coded legal conclusions. |
| REVIEW-REQ-005 | Keep raw source content, full file bodies, page images, unredacted personal data, credentials, hidden permission data, and deletion execution out of public payloads. |
| REVIEW-REQ-006 | Keep policy-pack version, organization-model version, permission boundary fingerprint, and review-support rules fingerprint visible for audit and evaluation. |
| REVIEW-REQ-007 | Reject or neutralize denied review attempts even if the UI is bypassed. |
| REVIEW-REQ-008 | Keep the stage deterministic, reproducible, zero-model-call, and zero-paid-service for P0 affordability. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Keep static `reviewSupport.json` only | Fast | Disconnects support from current scan and actor permissions | Rejected |
| Compute review support from assembled finding, governance config, and permission boundary | Connected, auditable, contract-compatible | Requires one explicit mock boundary | Accepted |
| Add a production authorization provider now | Realistic future path | Out of P0 scope and cost/risk boundary | Rejected |
| Hide denied actions until submit | Small UI payload | Surprising denial and weak accountability | Rejected |
| Expose allowed and denied actions before submit | Clear reviewer control | Requires visible permission metadata | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Waiting for finding assembly | Finding assembly pending | Evidence cards are not complete | Waiting for finding assembly | Return pending support summary |
| Waiting for finding assembly | Finding assembly completed | Evidence cards are assembled | Calculating permission boundary | Load actor, active policy pack, organization model, and finding owner |
| Calculating permission boundary | Actor recognized | Actor has review role, owner role, or Master of Data role | Review support ready | Return available decisions, denied actions, checklist, transfer options, and escalation options |
| Calculating permission boundary | Actor lacks review permission | Actor may only view | Review support limited | Return denied review decisions with reasons |
| Review support ready | Reviewer submits allowed decision | Decision is in available decisions and reason exists | Review command accepted | Human review command can create audit event |
| Review support ready | Reviewer submits denied decision | Decision is outside boundary | Review command rejected | Show denial reason; no finding, audit, or source state changes |
| Review support ready | Reviewer omits required reason or target | Required field missing | Review command rejected | Show validation reason; no finding, audit, or source state changes |
| Review support ready | Policy or org model changes | Version changes | Boundary stale | Recalculate support with the new version before future decisions |

## Failure Paths

- Missing assembled finding: return existing support fixture or neutral empty decisions; do not create review state.
- Missing policy review decisions: return no decisions and a warning instead of inventing actions.
- Missing transfer target: allow other decisions and return an empty transfer list.
- Missing escalation path: allow non-escalation decisions and return an empty escalation list.
- Actor outside boundary: return denied decision reasons and reject submit.
- Not-ready source: do not create scan, finding assembly, review support, permission boundary, audit, or metric changes.

## Rollback Path

1. Remove the optional `scan.reviewSupport`, metrics, and evaluation fields.
2. Keep `/api/users/me/permissions` and `/api/findings/{findingId}/review-support` mocks as static contract fixtures.
3. Keep existing finding detail allowed/denied actions.
4. Disable permission-aware mock review validation and keep UI-level required reason checks.

This rollback does not require a contract version bump because all added fields are optional under the tolerant contract.

## Impact Surface

- `contracts/schemas/source-scan.yaml`, `contracts/schemas/metrics.yaml`, and `contracts/schemas/governance.yaml` gain optional fields only.
- `contracts/mocks/scanStatus.json`, `reviewSupport.json`, `permissionBoundary.json`, `governanceConfig.json`, `adminMetrics.json`, and `evaluationLatest.json` stay envelope-compatible.
- Frontend mock workflow gains `frontend/src/data/reviewSupport.ts` and connects it through scan completion, finding detail review dialog, metrics, and evaluation.
- Tests add behavior coverage for support derivation, permission denial, reason/target validation, and not-ready source continuity.

## Primitive Acceptance Criteria

- A completed scan exposes `preparing_review_support` after `assembling_findings`.
- Completed scan state exposes `reviewSupport` with policy-pack version, organization-model version, support rules fingerprint, supported finding count, allowed action count, denied action count, decision count, required reason count, checklist count, transfer count, escalation count, `rawContentExposed = false`, and `legalConclusionProvided = false`.
- A finding-specific support payload includes all P0 review decisions that the actor may take: `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate`.
- Every available review decision requires a reason.
- The permission boundary exposes denied `execute_real_deletion` because P0 deletion remains simulated.
- A denied actor receives no review decisions and validation rejects attempted review submission.
- Missing reason, missing transfer target, and missing escalation queue reject submission before finding, audit, or source state changes.
- Evaluation preserves a review-support rules hash and keeps model calls and estimated paid-service cost at zero.
- Public payloads and support text do not expose raw source content, unredacted personal data, credentials, legal conclusions, or deletion execution.
