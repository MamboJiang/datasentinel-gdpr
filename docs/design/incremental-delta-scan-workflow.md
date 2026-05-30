# Incremental Delta Scan Workflow

## Problem Definition

After a full scan creates a source snapshot, file fingerprints, findings, review support, audit context, and evaluation traceability, DataSentinel needs an ongoing governance step that can represent changed-file-only processing. The step must connect to the completed full-scan baseline instead of behaving like an isolated static mock.

This P0 slice implements deterministic delta-scan execution and representation in the existing frontend mock workflow. It applies the repository Atlas reference in `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md` and the continuity requirements recorded in the inventory/extraction, deterministic signal-detection, context/risk, owner-routing, finding-assembly, review-support, human-review, and audit-event design notes.

## Scope

Included:

- Baseline guard: a delta scan can start only when a completed scan for the selected source can provide a prior full-scan baseline or a delta scan that still preserves that baseline.
- Optional scan-level `deltaScan` summary with baseline identity, changed/new/modified/unchanged/missing counts, carried-forward counts, reopened finding counts, and safety-boundary booleans.
- Dashboard and Sources actions that expose delta-scan readiness from the selected source, not from a hard-coded source.
- Pipeline visibility through `comparing_delta_baseline` before changed-file inventory and extraction.
- Metrics and evaluation traceability for changed-file-only processing.
- Audit events for delta scan start and completion through the existing structured audit-event boundary.

Excluded:

- Production Microsoft Graph, OAuth, tenant, webhook, delta-token, or SharePoint/OneDrive integration.
- Runtime parser, OCR, AI, queue, database, workflow engine, ticketing, notification, retention-label, or deletion service.
- Automatic deletion or treating missing source files as DataSentinel deletion.
- Legal conclusions, legal advice, or claims of full GDPR compliance.
- New public endpoints or required contract fields.

## Research Basis

- `docs/API_CONTRACT.md` already defines `POST /api/scans/delta` with tolerant optional fields and `application/problem+json` failure behavior.
- `docs/GOVERNANCE_CONFIG.md` requires policy-pack and organization-model continuity rather than hard-coded legal snapshots.
- `docs/EVALUATION.md` requires reproducibility, throughput, resource intensity, and zero P0 model cost where deterministic fixtures are used.
- GDPR Article 5 principles on data minimisation, storage limitation, integrity/confidentiality, and accountability support scanning only changed files after a baseline when the purpose is ongoing governance and the implementation remains auditable.
- Microsoft Graph delta query and OneDrive/SharePoint scan guidance are credible future connector references because Microsoft documents change tracking for new, updated, or deleted entities without full reads. P0 does not integrate those APIs.

References:

- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- Microsoft Graph delta query overview: https://learn.microsoft.com/en-us/graph/delta-query-overview
- OneDrive/SharePoint scan guidance: https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/scan-guidance

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| DELTA-REQ-001 | A delta scan must depend on a completed baseline; it cannot invent source history. |
| DELTA-REQ-002 | The baseline must preserve scan ID, source snapshot identity, inventory fingerprint, baseline file count, and baseline finding count for audit and evaluation continuity. |
| DELTA-REQ-003 | Delta processing must represent changed, new, modified, unchanged, and missing source files separately. |
| DELTA-REQ-004 | Unchanged files must be carried forward and must not be counted as newly scanned findings unless policy context later requires reopening. |
| DELTA-REQ-005 | Missing source files are source inventory changes, not DataSentinel deletion or proof of erasure. |
| DELTA-REQ-006 | Delta findings must still pass through deterministic signal detection, context/risk, owner routing, finding assembly, review support, audit, and evaluation boundaries. |
| DELTA-REQ-007 | Public payloads and UI must not expose raw source content, unredacted personal data, credentials, hidden permissions, legal conclusions, or deletion execution. |
| DELTA-REQ-008 | The P0 implementation must stay deterministic, zero-model-call, zero-estimated-paid-service-cost, and economically affordable. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Add production Graph delta query now | Reuses mature Microsoft change tracking | Requires tenant, auth, permissions, throttling, token storage, and privacy decisions outside P0 | Rejected |
| Add a new delta endpoint shape | Easy to tailor to UI | Breaks contract discipline because `/api/scans/delta` already exists | Rejected |
| Treat delta as a full scan with a different label | Minimal code | Does not prove baseline continuity or changed-file-only behavior | Rejected |
| Add optional `deltaScan` summary to existing scan payload | Contract-compatible, visible, reversible | Still fixture-backed until backend exists | Accepted |
| Use deterministic fixture counts and Vitest behavior tests | Free, reproducible, and sufficient for P0 | Does not prove production connector scaling | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Full scan completed | Delta scan requested | Selected source is scan-ready and has a completed baseline | Delta scan running | Create delta scan, attach baseline ID/fingerprint, record `delta_scan_started` |
| Delta scan requested | Baseline missing or mismatched | No completed baseline for selected source | Baseline unavailable | Reject without scan, audit, finding, metric, or evaluation change |
| Delta scan running | Baseline comparison starts | Baseline fingerprint exists | Comparing delta baseline | Count changed, new, modified, unchanged, and missing files |
| Comparing delta baseline | Comparison has partial progress | Running state is still active | Delta partial | Mark `meta.partial = true` and expose recoverable warnings |
| Comparing delta baseline | Changed files identified | Raw content remains internal | Inventorying changed files | Inventory only changed files and carry forward unchanged counts |
| Inventorying changed files | Extraction and deterministic signal detection complete | Redacted evidence signals exist | Downstream stages run | Context/risk, owner routing, finding assembly, review support, and audit use delta scan ID |
| Delta scan completed | Changed findings assembled | Metrics inputs exist | Delta scan completed | Publish changed-file findings, carried-forward counts, audit summary, and evaluation hashes |
| Delta scan completed | Missing files observed | No DataSentinel deletion occurred | Delta scan completed | Represent missing files as inventory changes with `deletionExecuted = false` |

## Public Contract Strategy

The endpoint set stays unchanged. `GET /api/scans/{scanId}` may include optional `deltaScan`:

- `baselineScanId`, `baselineSourceSnapshotId`, and `baselineInventoryFingerprint`
- `baselineTotalFiles` and `baselineFindingCount`
- `deltaFingerprint`
- `changedFiles`, `newFiles`, `modifiedFiles`, `unchangedFiles`, and `missingFiles`
- `processedChangedFiles`, `carriedForwardFiles`, `reopenedFindings`, and `unchangedFindingsCarriedForward`
- `missingFilesTreatedAsDeleted = false`, `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false`
- `warnings`

Admin metrics may include optional delta counters. Evaluation may include `deltaScanRulesHash`. Clients must ignore unknown fields and render missing optional delta data neutrally.

## Impact Surface

- `contracts/schemas/source-scan.yaml` and `contracts/schemas/metrics.yaml` gain optional delta fields.
- `docs/API_CONTRACT.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, `docs/EVALUATION.md`, `docs/FRONTEND_CONSOLE_CONTRACT.md`, and `ACCEPTANCE.md` gain the delta execution slice.
- `frontend/src/data` gains pure delta summary and scan metric helpers plus behavior tests.
- `frontend/src/pages/DashboardPage.tsx` and `frontend/src/pages/SourcesPage.tsx` expose baseline-aware delta actions and summaries.

## Rollback Path

1. Remove optional `scan.deltaScan`, optional delta metrics, and `evaluation.deltaScanRulesHash`.
2. Remove `comparing_delta_baseline` from delta pipeline representation.
3. Keep `/api/scans/delta` and `StartDeltaScanRequest` unchanged because they already exist in the contract.
4. Restore the previous Dashboard/Sources delta button behavior or disable delta until backend implementation.

Rollback does not require a contract version bump because required fields and endpoint paths remain unchanged.

## Primitive Acceptance Criteria

- A delta scan can start from the selected controlled source only when a completed baseline exists.
- A missing, running, not-ready, or mismatched baseline rejects before scan, audit, finding, metric, or evaluation state changes.
- Running delta scans expose `comparing_delta_baseline`, partial metadata, changed-file counts, baseline identity, and no raw-content/no-legal-conclusion/no-deletion boundaries.
- Completed delta scans process only changed files, carry unchanged baseline files forward, and represent missing files as source inventory changes rather than deletion.
- Completed delta findings use the delta scan ID and still pass through context/risk, owner routing, finding assembly, review support, audit recording, and evaluation.
- Dashboard and Sources expose delta readiness from the selected source and show baseline/change counts when available.
- Evaluation preserves a delta rules hash, deterministic reproducibility, throughput, zero model calls, and zero estimated paid-service cost.
- Behavior tests cover accepted delta start, rejected baseline paths, completed changed-file processing, carried-forward counts, no-real-deletion boundary, audit, metrics, evaluation, and full-scan continuity.
