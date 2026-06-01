# Evaluation Metrics Generation

## Problem Definition

lawdit needs an explicit evaluation stage after admin metrics aggregation. The current workflow exposes evaluation values, but the quality metrics must be generated from an auditable basis rather than treated as disconnected constants. The stage must show whether the scanner is measurable, reproducible, operationally affordable, and connected to accountable human review.

The repository Atlas reference in `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md` frames evaluation as proof that the system understands precision, recall, file-type and scenario variation, reproducibility, scan speed, resource intensity, review throughput, and risk reduction. This slice implements that requirement for the deterministic P0 mock workflow.

## Scope

In scope:

- Generate P0 evaluation metrics from prior workflow summaries and a controlled golden dataset definition.
- Preserve precision, recall, F1, reproducibility, throughput, resource intensity, review throughput, risk-reduction progress, scenario-level metrics, and safety boundaries.
- Keep evaluation linked to full scan, delta scan, context/risk, owner routing, finding assembly, review support, audit recording, human-review outcomes, and admin metrics aggregation.
- Keep model calls and estimated paid-service cost at zero for P0.

Out of scope:

- Production OCR, parser, AI, Microsoft Graph, Purview, OAuth, tenant, database, queue, or deletion integration.
- Legal advice, proof of full GDPR compliance, or proof of erasure.
- Downloading or vendoring the organizer sample repository.

## Research Basis

- Repository Atlas reference: `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md`.
- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- European Commission GDPR principles overview: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en
- NIST AI RMF 1.0: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
- OpenAPI 3.1.0: https://spec.openapis.org/oas/v3.1.0.html

These sources support treating evaluation as traceable measurement with privacy, accountability, minimisation, and contract compatibility constraints.

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| EVAL-REQ-001 | Evaluation must include precision, recall, reproducibility, scan speed, resource intensity, review throughput, and risk-reduction progress. |
| EVAL-REQ-002 | Precision and recall must be traceable to a controlled golden dataset and must not claim perfect detection. |
| EVAL-REQ-003 | Scenario-level results must show where false positives, false negatives, OCR-deferred files, or unsupported files affect trust. |
| EVAL-REQ-004 | Reproducibility must preserve dataset, deterministic signal-detection rules, policy-pack, config, stage fingerprints, and finding fingerprints. |
| EVAL-REQ-005 | Resource intensity must expose CPU, memory, model-call, API-cost, and zero-paid-service boundaries for P0 affordability. |
| EVAL-REQ-006 | Review throughput and risk-reduction progress must be human-accountable management metrics, not proof of deletion. |
| EVAL-REQ-007 | Delta evaluation must distinguish changed, carried-forward, missing, and reopened findings without treating missing files as deletion. |
| EVAL-REQ-008 | Rejected scan or review commands must leave evaluation state unchanged. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Keep static evaluation fixture values | Fast and simple | Does not prove connection to prior workflow stages | Rejected |
| Add a paid AI evaluation or OCR dependency | Could approximate production behavior | Expands cost, privacy, and dependency scope beyond P0 | Rejected |
| Use deterministic P0 golden-dataset formulas in TypeScript | Cheap, testable, reproducible, and contract-compatible | Not a production harness | Accepted |
| Add a separate evaluation endpoint per stage | More explicit API shape | Unnecessary public contract expansion | Rejected |

Future production candidates include scikit-learn-style confusion-matrix computation, MLflow-style run tracking, and batch data-quality tooling, but none are added until a backend harness and storage boundary are approved.

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Evaluation pending | Scan running | Upstream scan incomplete | Evaluation pending | Preserve previous completed evaluation and show pending pipeline stage |
| Evaluation pending | Scan completed | Inventory, extraction, context/risk, owner, finding, review-support, audit, and admin-metrics summaries exist | Metrics generated | Compute quality metrics, scenario metrics, resource intensity, hashes, and safety boundaries |
| Metrics generated | Review decision accepted | Decision passes permission, checklist, reason, target, and idempotency guards | Metrics refreshed | Refresh review throughput and risk-progress fields without changing scan-quality confusion matrix |
| Metrics generated | Review decision rejected | Guard fails | Metrics unchanged | Return rejection without evaluation, metric, audit, finding, or source mutation |
| Metrics generated | Delta scan completed | Completed baseline exists and delta summary is present | Delta metrics generated | Compute changed-file evaluation and preserve missing-file no-deletion boundary |

## Failure Paths

- Missing upstream summary: keep the previous evaluation and surface a neutral warning where the caller supports partial data.
- Missing golden-dataset entry: compute known fields only, set scenario metrics to an empty array, and keep precision, recall, and F1 nullable.
- Rejected scan or review command: preserve evaluation object identity.
- Unsupported or OCR-deferred files: count as quality warnings, not hidden failures.
- Safety-boundary violation in upstream summaries: expose the boundary boolean in evaluation instead of hiding it.

## Impact Surface

- `docs/EVALUATION.md`, `docs/API_CONTRACT.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, and `ACCEPTANCE.md`.
- `contracts/schemas/metrics.yaml` and `contracts/mocks/evaluationLatest.json`.
- Frontend mock workflow files in `frontend/src/data/`, evaluation types, and the Evaluation page.
- Behavior tests for scan completion, delta completion, review updates, rejected-path identity, safety boundaries, and metric formula correctness.

## Rollback Path

1. Remove optional evaluation quality-basis fields from `contracts/schemas/metrics.yaml` and mocks.
2. Remove the deterministic evaluation generator and revert callers to the previous `updateEvaluation` hash-only behavior.
3. Remove the evaluation pipeline stage from scan presentation.
4. Keep existing top-level precision, recall, F1, reproducibility, throughput, and resource-intensity fields because they already exist in the contract.

No endpoint or required-field change is introduced, so rollback does not require a contract version bump.

## Primitive Acceptance Criteria

- Completed full scans generate precision, recall, F1, reproducibility, throughput, resource intensity, confusion-matrix counts, scenario-level metrics, review throughput, risk-progress fields, and safety boundaries from prior summaries.
- Completed delta scans generate changed-file evaluation and preserve baseline, carried-forward, missing-file, no-raw-content, no-legal-conclusion, no-deletion, zero-model-call, and zero-cost boundaries.
- Evaluation exposes an evaluation-rules fingerprint plus detector/signal-detection and all upstream stage fingerprints needed for deterministic reproduction.
- Accepted human-review decisions refresh review-throughput and risk-progress fields exactly once without changing scan-quality precision, recall, or F1.
- Rejected scan or review commands leave evaluation, metric, audit, source, and finding state unchanged.
- The Evaluation page renders scan quality, confusion matrix, scenario metrics, resource intensity, reproducibility, and safety boundaries without raw source content or legal conclusions.
- Automated behavior tests cover full-scan generation, delta generation, review refresh, rejected-path identity, metric formula bounds, and cost/safety boundaries.
