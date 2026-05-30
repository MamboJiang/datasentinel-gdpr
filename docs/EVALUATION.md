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

## Evaluation Run Shape

```json
{
  "evaluationRunId": "eval_001",
  "scanId": "scan_001",
  "datasetHash": "sha256:demo_dataset",
  "scannerVersion": "0.1.0",
  "precision": 0.91,
  "recall": 0.84,
  "f1": 0.875,
  "reproducibility": 1.0,
  "throughputFilesPerSecond": 1.1,
  "resourceIntensity": {
    "peakMemoryMb": 410,
    "cpuSeconds": 18.4,
    "modelCalls": 0,
    "estimatedCostUsd": 0
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
- Context/risk rules fingerprint.
- Owner-assignment rules fingerprint.
- Finding-assembly rules fingerprint.
- Review-support rules fingerprint.
- Human-review decision rules fingerprint.
- Scanner version.
- Detector rules hash.
- Config hash.
- Policy pack version.
- Model name if an AI classifier is used.
- Model temperature if an AI classifier is used.
- Finding fingerprint.

## P0 Boundary

The first implementation may use deterministic mock evaluation values if the scanner is not complete. The UI and API shape must still match the contract so the real harness can replace mock values later.

For the inventory and extraction slice, resource intensity must stay explicit even though the workflow is fixture-backed. P0 uses zero model calls and zero estimated paid-service cost; unsupported or OCR-deferred files are represented as recoverable warnings rather than hidden failures.

For the context/risk judgment slice, evaluation must preserve the context-risk rules hash and policy-pack version while keeping model calls and estimated paid-service cost at zero. Context/risk output is deterministic review triage, not a legal conclusion.

For the owner-routing slice, evaluation must preserve the owner-assignment rules hash, policy-pack version, and organization-model version while keeping model calls and estimated paid-service cost at zero. Owner routing is deterministic accountability routing, not a legal conclusion or deletion action.

For the finding-assembly slice, evaluation must preserve the finding-assembly rules hash, policy-pack version, source snapshot, and completed finding fingerprint while keeping model calls and estimated paid-service cost at zero. Evidence cards are deterministic review support, not legal conclusions or deletion actions.

For the review-support slice, evaluation must preserve the review-support rules hash, policy-pack version, organization-model version, permission-boundary context, and supported-finding count while keeping model calls and estimated paid-service cost at zero. Review support is deterministic human decision support, not authorization infrastructure, legal advice, or deletion execution.

For the human-review decision slice, evaluation must preserve the human-review decision rules hash, policy-pack version, permission-boundary fingerprint, support-rule fingerprint, outcome counters, and backlog movement while keeping model calls and estimated paid-service cost at zero. Review decisions are human-accountable workflow commands, not automated legal conclusions or deletion execution.

For the audit-event recording slice, evaluation must preserve the audit-recording rules hash, event count, linked finding count, review-decision count, and no-raw-content/no-deletion boundaries while keeping model calls and estimated paid-service cost at zero. Audit recording is deterministic accountability evidence, not production log management or legal proof of compliance.

## Organizer Samples

The default evaluation source should reference `https://github.com/a-klumpp/GDPR-data-samples` and treat the sample families as controlled categories. The repository should not vendor the PDFs unless a separate storage and licensing decision is made.
