# Evaluation Harness

## Purpose

Evaluation is a product feature. DataSentinel must show that scanning quality is measurable, reproducible, fast enough for a prototype, and transparent about resource intensity.

## P0 Metrics

| Metric | Definition | Display Location |
| --- | --- | --- |
| Precision | True positives divided by predicted positives | Evaluation tab |
| Recall | True positives divided by actual positives | Evaluation tab |
| F1 | Harmonic mean of precision and recall | Evaluation tab |
| Reproducibility | Identical finding fingerprints across reruns | Evaluation tab |
| Throughput | Scanned files divided by scan duration | Admin dashboard |
| Resource intensity | Memory peak, CPU seconds, model calls, and estimated cost | Evaluation tab |
| Review throughput | Human review decisions recorded per review period | Admin dashboard |
| Review outcomes | Delete candidates, retained decisions, false positives, transfers, and escalations | Admin dashboard |
| Admin metrics reproducibility | Stable fingerprint of the management aggregation inputs and rules | Admin dashboard and Evaluation tab |
| Scenario quality | Precision, recall, F1, false positives, and false negatives by sample family | Evaluation tab |
| Risk-progress context | High-risk finding review progress without claiming deletion or legal compliance | Evaluation tab |
| AI spend guard | Optional OpenRouter model calls, estimated cost, configured budget, and fail-closed status | Evaluation tab and health metadata |

## Evaluation Run Shape

```json
{
  "evaluationRunId": "eval_001",
  "scanId": "scan_001",
  "datasetHash": "sha256:demo_dataset",
  "scannerVersion": "0.1.0",
  "precision": 0.941,
  "recall": 0.842,
  "f1": 0.889,
  "reproducibility": 1.0,
  "throughputFilesPerSecond": 1.1,
  "evaluationRulesHash": "sha256:evaluation_metrics_v1_demo",
  "qualityBasis": {
    "status": "computed",
    "goldenDatasetVersion": "gdpr-samples-p0-v1",
    "inputStages": ["file_inventory:completed"],
    "confusionMatrix": {
      "truePositives": 16,
      "falsePositives": 1,
      "falseNegatives": 3,
      "trueNegatives": 22,
      "predictedPositiveFiles": 17,
      "actualPositiveFiles": 19,
      "evaluatedFiles": 42
    }
  },
  "resourceIntensity": {
    "peakMemoryMb": 411,
    "cpuSeconds": 18.4,
    "modelCalls": 0,
    "estimatedCostUsd": 0,
    "estimatedCostPerThousandFilesUsd": 0,
    "paidServiceUsed": false
  }
}
```

## Reproducibility Requirements

Each scan should record:

- Dataset hash.
- Dataset source URL when applicable.
- Source snapshot ID.
- File inventory fingerprint.
- Content extraction fingerprint.
- Signal-detection rules fingerprint.
- Context/risk rules fingerprint.
- Owner-assignment rules fingerprint.
- Finding-assembly rules fingerprint.
- Review-support rules fingerprint.
- Admin-metrics aggregation rules fingerprint.
- Human-review decision rules fingerprint.
- Scanner version.
- Detector rules hash.
- Config hash.
- Policy pack version.
- Model name if an AI classifier is used.
- Model temperature if an AI classifier is used.
- OpenRouter model, budget baseline, model-call count, estimated cost, and fail-closed result if assistive AI is used.
- Finding fingerprint.
- Evaluation rules fingerprint.
- Confusion matrix and scenario-level quality basis.
- Review-throughput and risk-progress context.

## P0 Boundary

The first implementation may use deterministic mock evaluation values if the scanner is not complete. The UI and API shape must still match the contract so the real harness can replace mock values later.

For the inventory and extraction slice, resource intensity must stay explicit even though the workflow is fixture-backed. P0 uses zero model calls and zero estimated paid-service cost; unsupported or OCR-deferred files are represented as recoverable warnings rather than hidden failures.

For the deterministic signal-detection slice, evaluation must preserve the detector rules hash, policy-pack evidence requirements, evaluated evidence-candidate count, detected/redacted signal counts, findings-with-signals count, and signal-type counts while keeping model calls and estimated paid-service cost at zero. Signal detection is deterministic evidence generation, not legal advice or deletion execution.

`tests/core_engine_quality_report.py` is the reproducible deterministic-signal quality harness for the current core-engine corpus. It evaluates the multilingual text oracle cases and generated format challenges, then records only case IDs, language/format labels, expected signal types, actual signal types, type-level precision/recall/F1, and false-positive/false-negative type counts in `tests/fixtures/gdpr_data_samples_main/core_engine_quality_report.json`. The report must not store raw source text, raw detected values, source bodies, Drive URLs, page images, provider tokens, or private absolute paths.

For the context/risk judgment slice, evaluation must preserve the context-risk rules hash and policy-pack version while keeping model calls and estimated paid-service cost at zero. Context/risk output is deterministic review triage, not a legal conclusion.

For the owner-routing slice, evaluation must preserve the owner-assignment rules hash, policy-pack version, and organization-model version while keeping model calls and estimated paid-service cost at zero. Owner routing is deterministic accountability routing, not a legal conclusion or deletion action.

For the finding-assembly slice, evaluation must preserve the finding-assembly rules hash, policy-pack version, source snapshot, and completed finding fingerprint while keeping model calls and estimated paid-service cost at zero. Evidence cards are deterministic review support, not legal conclusions or deletion actions.

For the review-support slice, evaluation must preserve the review-support rules hash, policy-pack version, organization-model version, permission-boundary context, and supported-finding count while keeping model calls and estimated paid-service cost at zero. Review support is deterministic human decision support, not authorization infrastructure, legal advice, or deletion execution.

For the human-review decision slice, evaluation must preserve the human-review decision rules hash, policy-pack version, permission-boundary fingerprint, support-rule fingerprint, outcome counters, and backlog movement while keeping model calls and estimated paid-service cost at zero. Review decisions are human-accountable workflow commands, not automated legal conclusions or deletion execution.

For the audit-event recording slice, evaluation must preserve the audit-recording rules hash, event count, linked finding count, review-decision count, and no-raw-content/no-deletion boundaries while keeping model calls and estimated paid-service cost at zero. Audit recording is deterministic accountability evidence, not production log management or legal proof of compliance.

For the incremental delta-scan slice, evaluation must preserve the delta rules hash, baseline scan ID, baseline inventory fingerprint, changed-file counts, carried-forward counts, missing-file boundary, and completed delta finding fingerprint while keeping model calls and estimated paid-service cost at zero. Delta scanning is deterministic ongoing governance representation, not proof of deletion, production connector synchronization, or legal compliance.

For the admin-metrics aggregation slice, evaluation must preserve the admin-metrics rules hash, upstream stage basis, owner backlog, review outcome, audit evidence, delta boundary, and resource-cost context while keeping model calls and estimated paid-service cost at zero. Admin metrics are deterministic management evidence, not legal advice, production analytics storage, or proof of deletion.

For the evaluation-metrics generation slice, evaluation must generate precision, recall, F1, reproducibility, throughput, resource intensity, confusion-matrix counts, scenario-level metrics, review-throughput context, and risk-progress context from prior workflow summaries plus a controlled golden dataset definition. It must preserve an evaluation rules hash, expose false-positive and false-negative context, keep model calls and estimated paid-service cost at zero, and avoid presenting review progress as proof of deletion, legal advice, or full GDPR compliance.

For the OpenRouter AI assistive-processing slice, evaluation and health metadata must expose AI readiness and cost controls without making normal deterministic scans paid. Explicit AI calls must be counted as model calls with estimated cost, model ID, and budget status. Rejected AI preflights must leave scan quality, findings, audit, metrics, and evaluation state unchanged.

## Organizer Samples

The default evaluation source should reference `https://github.com/a-klumpp/GDPR-data-samples` and treat the sample families as controlled categories. The repository should not vendor the PDFs unless a separate storage and licensing decision is made.
