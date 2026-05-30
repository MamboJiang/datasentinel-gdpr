# GDPR Enterprise Atlas 12-Stage Design Audit

## Problem Definition

The user requested a full design audit of the 12 workflow stages against the GDPR Enterprise Expert Atlas and asked that the Atlas markdown be saved in the project. Developer-facing repository documentation must stay English-only, so the local Atlas was normalized into `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md`.

## Audit Basis

- Local source reviewed: `/Users/y.h/Downloads/GDPR_Enterprise_Expert_Atlas.md`, generated 2026-05-30.
- Repository reference: `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md`.
- Official references: GDPR on EUR-Lex, European Commission GDPR principles guidance, EDPB right-of-access guidance, and Microsoft Graph delta query documentation for future connector planning only.

## Impact Surface

- Product and technical docs under `docs/`.
- Acceptance criteria in `ACCEPTANCE.md`.
- Optional contract schemas and mocks under `contracts/`.
- Existing frontend mock workflow types and deterministic data modules.

No public endpoint, required field, production connector, OAuth flow, tenant integration, runtime parser, OCR, AI dependency, queue, database, or deletion execution is introduced.

## Gap Summary

| Stage | Existing status before audit | Gap found | Remediation |
| --- | --- | --- | --- |
| 1. Start full scan | Design existed. | Actor, idempotency, and active policy-pack inputs were less explicit than the Atlas/user stage list. | Updated full-scan design and acceptance to require actor, idempotency context, source readability/readiness, and policy-pack context. |
| 2. Inventory and extraction | Design existed. | Internal inventory item inputs needed clearer file path, size, modified time, sample family, and file fingerprint language. | Updated inventory/extraction design and acceptance language. |
| 3. Deterministic signal detection | Pipeline label and finding signals existed. | Missing independent design note, scan-level summary, acceptance section, metrics counters, and evaluation traceability. | Added `docs/design/deterministic-signal-detection.md`, optional `signalDetection`, signal metrics, rules hash, mocks, and tests. |
| 4. Context and risk | Design existed. | References still depended on prior Atlas-derived wording instead of the saved repository reference. | Updated references and stage continuity to include signal detection. |
| 5. Owner assignment | Design existed. | Older note said the local Atlas was not present. | Updated to reference the saved Atlas repository edition. |
| 6. Finding/evidence card | Design existed. | Older note said the local Atlas was not present. | Updated to reference the saved Atlas and signal-detection stage. |
| 7. Review support/permissions | Design existed. | Older note said the local Atlas was not present. | Updated to reference the saved Atlas and explicit signal continuity. |
| 8. Human review decisions | Design existed. | No blocking gap. | Kept no-real-deletion and idempotency boundaries; linked to saved Atlas. |
| 9. Audit events | Design existed. | No blocking gap. | Kept AuditEvent as first-class object; linked to saved Atlas. |
| 10. Incremental scan | Design existed. | Older note said the local Atlas was not present. | Updated to reference the saved Atlas and signal continuity. |
| 11. Admin metrics | Design existed. | Metrics did not expose signal-detection counters. | Added detected/redacted signal and findings-with-signals counters. |
| 12. Evaluation metrics | Design existed. | Evaluation did not preserve an explicit signal-detection rules hash. | Added `signalDetectionRulesHash` and `signal_detection` input-stage trace. |

## Stage State Machine Coverage

| Stage | State-machine source |
| --- | --- |
| Full scan start | `docs/design/full-scan-start-workflow.md` |
| Inventory and extraction | `docs/design/source-inventory-content-extraction.md` |
| Deterministic signal detection | `docs/design/deterministic-signal-detection.md` |
| Context and risk judgment | `docs/design/context-risk-judgment.md` |
| Owner routing | `docs/design/owner-routing-assignment.md` |
| Finding assembly | `docs/design/finding-assembly-evidence-card.md` |
| Review support and permission boundary | `docs/design/review-support-permission-boundary.md` |
| Human review decision handling | `docs/design/human-review-decision-handling.md` |
| Audit event recording | `docs/design/audit-event-recording.md` |
| Incremental delta scan | `docs/design/incremental-delta-scan-workflow.md` |
| Admin metrics aggregation | `docs/design/admin-metrics-aggregation.md` |
| Evaluation metrics generation | `docs/design/evaluation-metrics-generation.md` |

## Rollback Path

1. Remove `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md` and this audit note only if the team no longer wants repository-local Atlas traceability.
2. Remove the optional `signalDetection` schema, mock, type, metrics, and evaluation fields.
3. Keep existing `detecting_signals` pipeline label and finding `signals` payload because they predated this audit and remain part of the P0 contract.
4. Revert doc references from the signal-detection stage back to the broader inventory/extraction and context/risk stages.

Rollback does not require a contract version bump because all added wire fields are optional under the tolerant contract.

## Primitive Acceptance Criteria

- The repository contains an English Atlas reference under `docs/reference/`.
- Every one of the 12 user-listed stages has a design note with scope, state transitions, failure paths, rollback path, and primitive acceptance criteria.
- The contract and mocks can represent the 12-stage workflow without exposing raw source content or executing deletion.
- Admin metrics and evaluation expose deterministic signal-detection traceability.
- `ACCEPTANCE.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, and `docs/EVALUATION.md` stay synchronized.
