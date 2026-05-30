# Source Inventory and Content Extraction

## Problem Definition

After a controlled source starts a full scan, DataSentinel needs an observable step that turns source metadata into file candidates and content extraction outcomes. The step must be useful for GDPR discovery without becoming a second repository of raw sensitive content.

This document defines the P0 implementation slice for source inventory and content extraction. It follows the existing source -> scan -> finding -> review -> audit -> delta -> evaluation loop and the repository Atlas reference in `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md`.

## Scope

In scope:

- Deterministic sample-source file inventory summaries.
- Internal file inventory items with path, size, modified timestamp, sample family, permission snapshot, readability status, and stable file fingerprint.
- Deterministic content extraction summaries for text, metadata, table, and deferred OCR handling.
- Redacted evidence-candidate counts only, not raw extracted text.
- Scan-stage visibility through the existing scan, metrics, audit, and evaluation surfaces.
- Partial-data warnings while the scan is running.
- Resource and cost transparency for the P0 mock workflow.

Out of scope:

- Production Microsoft Graph, OAuth, tenant, or deletion integrations.
- Downloading or vendoring organizer sample files.
- Runtime OCR, parser, NER, LLM, storage, queue, or database selection.
- Automatic deletion, legal conclusions, or unreviewed retention decisions.
- New public extraction endpoints.

## Research Basis

- `docs/API_CONTRACT.md` keeps the public P0 API stable and tolerant of optional fields.
- `docs/GOVERNANCE_CONFIG.md` requires policy-pack guidance instead of hard-coded legal snapshots.
- `docs/EVALUATION.md` requires reproducibility, throughput, and resource intensity.
- GDPR Article 5 principles and European Commission guidance support data minimisation, storage limitation, integrity, confidentiality, and accountability as system constraints.
- Apache Tika is a credible future production candidate because its official documentation describes metadata and text extraction across many file types through one interface.
- Tesseract is a credible future OCR candidate because its official documentation describes an open-source OCR engine with language data packages.
- Microsoft Graph delta query is relevant only for a future connector because official Microsoft documentation describes change tracking for new, updated, or deleted entities without full reads.

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| INVEXT-REQ-001 | Build a file inventory baseline before findings are assembled. |
| INVEXT-REQ-002 | Preserve file path, size, modified timestamp, sample family, source snapshot identity, and file fingerprints internally for reproducibility and delta scans. |
| INVEXT-REQ-003 | Extract only enough content-derived evidence to support redacted evidence candidates. |
| INVEXT-REQ-004 | Keep raw extracted text inside an internal boundary and expose `rawContentExposed = false` in P0. |
| INVEXT-REQ-005 | Represent unsupported or unreadable files as warnings when recoverable. |
| INVEXT-REQ-006 | Use deterministic evidence-first processing; AI/model calls remain zero in this slice. |
| INVEXT-REQ-007 | Track resource intensity and estimated cost so the workflow stays economically affordable. |
| INVEXT-REQ-008 | Preserve owner, Master of Data, retention, permission, audit, and evaluation continuity for later stages. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Add production parsers now | Closer to pilot reality | Adds runtime, security, and cost decisions before source boundaries are approved | Rejected for P0 |
| Add one public extraction endpoint | Easy to debug stage output | Expands API surface and risks raw-content leakage | Rejected |
| Add optional scan-stage summaries to existing scan payload | Keeps frontend/backend contract stable and observable | Requires disciplined optional-field handling | Accepted |
| Use deterministic fixture-backed summaries | Fast, free, reproducible, and testable | Does not parse real documents | Accepted for P0 |
| Use Tika/Tesseract later behind an internal boundary | Reuses mature open-source tools and controls cost | Needs sandboxing, file-size limits, and parser hardening | Future candidate |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Scan running | Inventory starts | Source is scan-ready | Inventorying files | Create source snapshot ID and candidate counts |
| Inventorying files | Inventory completes | At least one candidate exists | Extracting content | Store stable file fingerprints and family counts |
| Inventorying files | Inventory has recoverable gaps | Source remains readable | Extracting content with warnings | Mark partial data and keep warning messages |
| Inventorying files | Inventory fails | Failure is blocking | Scan failed | Keep prior findings intact and emit problem details in backend implementations |
| Extracting content | Supported content parsed | Raw text remains internal | Extraction summarized | Count successful files and redacted evidence candidates |
| Extracting content | File unsupported or OCR deferred | Failure is recoverable | Extraction summarized with warnings | Count warning files without exposing raw content |
| Extraction summarized | Scan continues | Deterministic signal detection is next | Detecting signals | Downstream stages may create findings from redacted evidence candidates |
| Extraction summarized | Scan completes | Metrics are available | Scan completed | Publish final counts, duration, throughput, and evaluation links |

## Public Contract Strategy

The public contract does not gain a new endpoint. The scan payload may include optional fields:

- `stage`: current internal scan stage.
- `pipelineStages`: ordered internal stage summaries.
- `fileInventory`: candidate counts, fingerprints, family distribution, skipped files, and source snapshot ID.
- `contentExtraction`: extraction status, method counts, warning counts, redacted evidence candidate count, and `rawContentExposed`.

Internal inventory items use the minimum shape `filePath`, `sizeBytes`, `modifiedAt`, `sampleFamily`, `fileFingerprint`, `readabilityStatus`, and `permissionSnapshotId`. Public P0 scan payloads expose aggregate counts and fingerprints, not the raw internal extracted text.

The admin metrics payload may include optional inventory and extraction counters. Clients must continue to ignore unknown fields.

## Privacy and Security Boundaries

- Do not expose raw source text, full file bodies, page images, or unredacted personal data.
- Redacted evidence snippets remain part of finding evidence cards, not this inventory/extraction summary.
- Warning text must describe processing limitations without copying source content.
- Parser/OCR execution is deferred until sandboxing, file-size limits, MIME allowlists, and malware handling are designed.
- P0 uses zero model calls and zero paid services.

## Economic Affordability

P0 remains deterministic and cost-free. A later production path should prefer this order:

1. Metadata and file fingerprinting for all candidates.
2. Text-layer extraction for supported files.
3. Deterministic pattern detectors.
4. OCR only for suspicious or sampled image/PDF files.
5. AI context classification only when deterministic context is insufficient and policy allows it.

This order minimizes expensive OCR/model usage while preserving auditability and reproducibility.

## Rollback Path

If this slice creates UI or contract noise, remove the optional scan and metrics fields while keeping the existing full-scan start workflow unchanged. No endpoint or required field changes are introduced, so rollback does not require a contract version bump.

## Primitive Acceptance Criteria

- Starting a full scan creates visible file-inventory and content-extraction summaries for the selected source.
- Internal inventory has file path, size, modified timestamp, sample family, fingerprint, and readability status for each candidate file.
- Running scans mark partial data and show recoverable warnings without creating raw-content exposure.
- Completing the scan marks inventory and extraction stages complete and preserves deterministic evaluation with zero model calls.
- Optional fields remain compatible with the existing `ScanEnvelope` and `AdminMetricsEnvelope`.
- Unsupported or OCR-deferred files are counted as warnings, not fatal errors.
- The UI shows candidate files, fingerprinted files, extracted files, redacted evidence candidates, warning counts, and raw-content boundary status.
- Behavior tests cover running, completed, partial-warning, no-raw-content, and not-ready-source paths.
