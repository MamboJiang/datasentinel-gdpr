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
- Scanner version.
- Detector rules hash.
- Config hash.
- Model name if an AI classifier is used.
- Model temperature if an AI classifier is used.
- Finding fingerprint.

## P0 Boundary

The first implementation may use deterministic mock evaluation values if the scanner is not complete. The UI and API shape must still match the contract so the real harness can replace mock values later.
