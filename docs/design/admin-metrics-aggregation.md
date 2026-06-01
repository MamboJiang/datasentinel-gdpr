# Admin Metrics Aggregation

## Problem Definition

lawdit needs a management metrics stage that turns the prior workflow stages into accountable operational evidence. The repository Atlas reference in `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md` positions the product as a responsible deletion control tower, where management cares about source coverage, risk reduction, owner backlog, review throughput, outcomes, cost, and evidence rather than raw PII counts alone.

This P0 slice implements deterministic, fixture-backed aggregation for the existing mock workflow. It does not add production connectors, Microsoft Graph/OAuth, a database, AI/OCR services, legal advice, or deletion execution.

## Research Basis

- Repository Atlas reference: `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md`.
- GDPR accountability, purpose, retention, and audit context are grounded in Regulation (EU) 2016/679, especially the principles and records-of-processing expectations.
- EDPB Guidelines 01/2022 reinforce that access-right workflows need implementation detail and evidence handling, not just search output.
- Microsoft Graph delta query is noted as a future production candidate because it supports change tracking without repeated full reads, reducing operating cost. P0 keeps it as documentation only.
- OpenAPI 3.1 remains the machine-readable contract basis for optional fields and forward-compatible schema evolution.

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| METRICS-REQ-001 | Metrics must represent a control-tower view: source coverage, risk, owner backlog, outcomes, trend inputs, audit evidence, speed, and cost. |
| METRICS-REQ-002 | Metrics must be derived from prior workflow stages instead of disconnected dashboard constants. |
| METRICS-REQ-003 | Management output must include deterministic signal-detection counts but must not expose raw source content, unredacted personal data, legal conclusions, hidden permission data, or deletion execution. |
| METRICS-REQ-004 | Owner backlog and review throughput must be first-class because the product should not create unmanageable review queues. |
| METRICS-REQ-005 | Delta metrics must distinguish changed, unchanged, and missing files; missing files are inventory changes, not proof of deletion. |
| METRICS-REQ-006 | Cost affordability must be visible through resource intensity, model calls, and estimated service cost. |
| METRICS-REQ-007 | Evaluation must preserve an admin-metrics rules fingerprint for reproducibility. |
| METRICS-REQ-008 | Rejected commands must leave metric state unchanged. |

## Options Considered

| Option | Benefit | Cost / Risk | Decision |
| --- | --- | --- | --- |
| Keep flat dashboard counters only | Minimal code | Counters do not prove source, risk, review, audit, and evaluation continuity | Rejected |
| Add a pure frontend aggregation boundary | Testable, reversible, no new dependency, matches current P0 fixture architecture | Still mock-backed until backend exists | Accepted |
| Add analytics database or BI layer now | Enterprise-like trend storage | Requires persistence, auth, retention, privacy, deployment, and cost decisions outside P0 | Rejected |
| Add Graph/Purview integration now | Real enterprise connector signal | Violates P0 scope and credential/tenant constraints | Rejected |

## State Machine

| Current State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Prior stages unavailable | Metrics requested | Missing scan stage summaries | Metrics unavailable | Return neutral optional values or existing fixture data |
| Scan running | Metrics aggregated | Inventory or downstream stage is pending | Metrics partial | Update running scan, risk, owner, audit, and delta counters; mark partial and include warnings |
| Scan completed | Metrics aggregated | All prior summaries are available | Metrics completed | Update scan coverage, risk, owner backlog, outcomes, audit, resource, and evaluation-linked summary |
| Review supported | Review decision accepted | Decision passes permission, reason, checklist, target, and idempotency guards | Metrics completed | Increment outcome, backlog, throughput, audit, and evaluation-linked metrics once |
| Review supported | Review decision rejected | Guard fails | Metrics unchanged | Return rejection reason without metric, audit, finding, source, or evaluation mutation |
| Baseline completed | Delta scan completed | Changed-file workflow completes | Metrics completed | Include changed/new/modified/unchanged/missing counts and no-deletion boundary |

## Failure Paths

- Missing upstream summary: render the previous known metrics and neutral optional aggregation state.
- Running partial scan: set `aggregation.status = partial`, keep numeric metrics bounded, and expose warnings.
- Rejected scan or review command: keep the exact prior metrics object unchanged.
- Duplicate review idempotency key: return the existing accepted result without duplicate metric increments.
- Any unsafe boundary flag from upstream summaries must propagate to aggregation booleans instead of being hidden.

## Impact Surface

- `contracts/schemas/metrics.yaml` gains optional `data.aggregation` and `evaluation.adminMetricsRulesHash`.
- `contracts/mocks/adminMetrics.json` and `contracts/mocks/evaluationLatest.json` include the optional aggregation summary.
- `docs/API_CONTRACT.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, `docs/EVALUATION.md`, and `ACCEPTANCE.md` describe the stage.
- Frontend mock workflow uses a pure aggregation module for running scans, completed scans, delta scans, and review decisions.
- Dashboard shows management indicators without exposing raw content or implying deletion execution.

## Rollback Path

1. Remove optional `AdminMetrics.aggregation` and `EvaluationSummary.adminMetricsRulesHash` fields from contract schemas, mocks, and frontend types.
2. Remove `frontend/src/data/adminMetricsAggregation.ts` and revert callers to flat metric updates.
3. Remove the Dashboard management-indicators panel and this acceptance section.
4. Existing required fields and endpoints remain unchanged, so rollback does not require a contract version bump.

## Primitive Acceptance Criteria

- Running scans expose partial metrics whose input stages identify the upstream stage status.
- Completed scans expose completed metrics whose scan, risk, owner, review, audit, resource, and evaluation values match upstream summaries.
- Delta scans expose changed-file metrics and preserve `missingFilesTreatedAsDeleted = false` and `deletionExecuted = false`.
- Accepted review decisions update owner backlog, outcome counters, audit counts, and evaluation-linked aggregation exactly once.
- Rejected scan or review attempts leave metrics unchanged by object identity in the mock workflow.
- Aggregated metrics expose `rawContentExposed = false`, `legalConclusionProvided = false`, `deletionExecuted = false`, `modelCalls = 0`, and `estimatedCostUsd = 0` for P0.
- Evaluation preserves the admin metrics aggregation rules fingerprint.
- Automated behavior tests cover running, completed, delta, accepted review, rejected path, safety boundaries, and cost boundary.
