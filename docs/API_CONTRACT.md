# API Contract

## Purpose

This contract lets frontend and backend agents work in parallel without blocking each other. It is intentionally broad and tolerant for the hackathon prototype while still giving stable shapes for UI, backend, mocks, and tests.

Source of truth:

- Machine-readable contract: `contracts/openapi.yaml`.
- Mock payloads: `contracts/mocks/`.
- Design rationale: `docs/design/frontend-backend-delivery-contract.md`.
- Adaptive governance rationale: `docs/design/adaptive-governance-review-control.md`.

## Standard Basis

- OpenAPI 3.1 describes HTTP APIs and aligns schema objects with JSON Schema 2020-12: https://spec.openapis.org/oas/v3.1.0.html
- JSON Schema allows additional object properties by default and can model extension-friendly objects: https://json-schema.org/understanding-json-schema/reference/object
- RFC 9457 defines `application/problem+json` for HTTP API error details: https://www.rfc-editor.org/rfc/rfc9457.html

## Contract Strategy

Use `OpenAPI-first + mock-first + vertical-slice-first`.

- OpenAPI-first: all endpoint shapes are documented before implementation.
- Mock-first: frontend can render the full P0 flow from static payloads.
- Vertical-slice-first: backend should implement one complete source -> scan -> finding -> review -> audit path before broad feature work.

## Wire Format

- Base path: `/api`.
- JSON field names: lower camel case.
- IDs are opaque strings, such as `scan_001`.
- Dates use ISO 8601 UTC strings.
- Legal conclusions and raw sensitive values are not part of P0 payloads. Optional AI budget metadata may expose bounded operational cost limits and estimated service cost without exposing billing credentials.
- Sensitive snippets must be redacted.

## Response Envelope

Every successful response returns:

```json
{
  "data": {},
  "meta": {
    "contractVersion": "0.1.0",
    "generatedAt": "2026-05-30T12:00:00Z",
    "traceId": "trace_demo_001",
    "partial": false,
    "warnings": []
  }
}
```

List responses may also include:

```json
{
  "pagination": {
    "limit": 25,
    "offset": 0,
    "total": 42,
    "nextCursor": null
  }
}
```

## Tolerance Rules

- Clients must ignore unknown fields.
- Servers may add optional fields without changing the contract version.
- Clients must handle missing optional fields, `null` optional objects, and empty arrays.
- Enum-like values are open strings. Unknown values must render as `unknown` or a neutral fallback.
- Numeric metrics may be `null` while a scan is running.
- `meta.partial = true` means the UI may render available data with a warning.
- Backend should preserve stable IDs within a demo seed.
- Permission-aware endpoints should return both allowed and denied actions when available.
- Policy guidance should include policy-pack version, not hard-coded legal conclusions.

## Required Headers

Requests should send:

- `Accept: application/json, application/problem+json`
- `X-Contract-Version: 0.1.0`
- `X-Actor-Id: user_demo_admin` or a seeded demo user.
- `Idempotency-Key` for review actions and scan start requests when available.

Responses should include:

- `X-Trace-Id`
- `X-Contract-Version`

## Error Format

Errors use `application/problem+json`.

```json
{
  "type": "https://datasentinel.local/problems/validation-error",
  "title": "Request validation failed",
  "status": 422,
  "detail": "The request body is invalid.",
  "instance": "/api/scans/full",
  "traceId": "trace_demo_001",
  "errors": [
    {
      "pointer": "#/sourceId",
      "detail": "sourceId is required"
    }
  ]
}
```

## P0 Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check backend readiness. |
| `GET` | `/api/sources` | List configured sources. |
| `POST` | `/api/sources` | Create a local or mock source. |
| `POST` | `/api/sources/{sourceId}/connect-test` | Validate source reachability. |
| `POST` | `/api/scans/full` | Start a full scan for a connected or mock-ready source. |
| `POST` | `/api/scans/delta` | Start a delta scan. |
| `GET` | `/api/scans/{scanId}` | Read scan status and progress. |
| `GET` | `/api/scans/{scanId}/summary` | Read KPI summary for one scan. |
| `GET` | `/api/findings` | List findings for admin or owner views. |
| `GET` | `/api/findings/{findingId}` | Read an evidence card. |
| `POST` | `/api/findings/{findingId}/review` | Record a human review decision. |
| `GET` | `/api/audit/events` | List audit events. |
| `GET` | `/api/admin/metrics` | Read admin dashboard metrics. |
| `GET` | `/api/evaluation/runs/latest` | Read latest evaluation summary. |
| `GET` | `/api/governance/config` | Read active governance configuration. |
| `GET` | `/api/governance/policy-packs/active` | Read active policy pack. |
| `POST` | `/api/governance/changes/preview` | Preview policy or organization change impact. |
| `GET` | `/api/users/me/permissions` | Read current actor permission boundary. |
| `GET` | `/api/findings/{findingId}/review-support` | Read reviewer guidance and allowed actions. |

## State Machines

### Optional AI Processing Metadata

`GET /api/health`, scan payloads, admin metrics, and evaluation summaries may include optional `ai` or `aiProcessing` metadata. This metadata is informational and must never include the OpenRouter API key or raw source content.

Representative shape:

```json
{
  "status": "configured",
  "mode": "assistive",
  "provider": "openrouter",
  "model": "google/gemini-3.1-flash-lite",
  "budgetLimitEur": 25,
  "budgetLimitUsd": 25,
  "usageBaselineUsd": 0,
  "budgetGuard": "fail_closed",
  "atlasReference": "docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md",
  "atlasAlignment": [
    { "stage": 1, "name": "start_full_scan" },
    { "stage": 12, "name": "evaluation_metrics" }
  ],
  "tierPlan": [
    { "tier": "source_policy_context", "provider": "local_policy_pack", "mode": "deterministic", "status": "enabled", "atlasStages": [1] },
    { "tier": "metadata_inventory", "provider": "local", "mode": "deterministic", "status": "enabled", "atlasStages": [2] },
    { "tier": "ocr", "provider": "local_tesseract", "mode": "deferred", "status": "deferred", "atlasStages": [2] },
    { "tier": "grep_rules", "provider": "local_regex", "mode": "deterministic", "status": "enabled", "atlasStages": [3] },
    { "tier": "policy_context_risk", "provider": "local_policy_pack", "mode": "deterministic", "status": "enabled", "atlasStages": [4] },
    { "tier": "ai_context", "provider": "openrouter", "mode": "assistive", "status": "configured", "atlasStages": [4], "role": "redacted_context_support_only" },
    { "tier": "review_permission_boundary", "provider": "local_governance", "mode": "human_accountable", "status": "enabled", "atlasStages": [6, 7, 8] },
    { "tier": "audit_recording", "provider": "local_audit", "mode": "deterministic", "status": "enabled", "atlasStages": [9] },
    { "tier": "delta_evaluation_metrics", "provider": "local_metrics", "mode": "deterministic", "status": "enabled", "atlasStages": [10, 11, 12] }
  ],
  "modelCalls": 0,
  "estimatedCostUsd": 0,
  "paidServiceUsed": false,
  "rawContentExposed": false,
  "legalConclusionProvided": false,
  "deletionExecuted": false
}
```

AI processing state:

- `disabled`: `DATASENTINEL_AI_MODE` is off.
- `missing_api_key`: assistive mode is requested without `OPENROUTER_API_KEY`.
- `configured`: OpenRouter key and model are configured, but no call has necessarily occurred.
- `usage_check_failed`: fail-closed budget preflight prevented a call because usage could not be checked.
- `budget_exceeded`: project budget or OpenRouter remaining limit prevented a call.
- `ready`: a redacted, deterministic evidence candidate may be sent to OpenRouter by an explicit assistive classification path.

The processing order is `source_policy_context -> metadata_inventory -> text_layer -> ocr -> grep_rules -> policy_context_risk -> ai_context -> owner_assignment_boundary -> review_permission_boundary -> audit_recording -> delta_evaluation_metrics`. AI escalation is optional Atlas stage-4 context support and requires redacted evidence, deterministic anchors, and active policy-pack context. Public payloads must not expose raw extracted text, full file bodies, page images, credentials, unredacted personal data, legal conclusions, owner decisions, permission decisions, audit facts invented by AI, or deletion instructions.

### Scan Status

Start guard:

- `POST /api/scans/full` requires `sourceId`.
- P0 accepts full-scan start for the controlled `mock_ready` organizer sample source.
- A source that is missing, unreadable, or not scan-ready must not create a scan record; backend implementations should return `application/problem+json`, and mock UI implementations should show a neutral denial message.
- Accepted scan starts should be idempotent when `Idempotency-Key` is present.
- `POST /api/scans/delta` requires `sourceId` and a completed selected-source baseline; when `baselineScanId` is provided it must match an available baseline. Missing, running, not-ready, or mismatched baselines must not create scan, audit, finding, metric, or evaluation state changes.

`queued -> running -> completed`

Failure paths:

- `queued -> failed`
- `running -> failed`
- `running -> cancelled`

Retry path:

- `failed -> queued`

Internal P0 stage visibility:

- `source_ready -> inventorying_files -> extracting_content -> detecting_signals -> judging_context_risk -> assigning_owner -> assembling_findings -> preparing_review_support -> recording_audit_events -> completed`
- Delta scans may insert `comparing_delta_baseline` after `source_ready` and before `inventorying_files`.
- Inventory, extraction, context/risk, owner-assignment, finding-assembly, review-support, and audit-recording stages are exposed as optional scan summaries, not as public endpoints.
- Running scans may return `meta.partial = true` with recoverable inventory or extraction warnings.
- Public scan payloads must not expose raw extracted text, full source content, page images, or unredacted personal data.
- `rawContentExposed = false` is the required P0 value when extraction status is visible.
- Signal detection output may include `signalDetection` with detector rules version/hash, active evidence requirements, evaluated evidence-candidate count, detected/redacted signal count, findings-with-signals count, signal-type counts, warnings, and `rawContentExposed = false`.
- Deterministic signal detection is evidence generation only; public payloads must not expose raw extracted text, unredacted snippets, detector secrets, legal conclusions, or deletion execution.
- `contextRisk.legalConclusionProvided = false` is the required P0 value when context/risk status is visible.
- Context/risk output must include policy-pack version and must use neutral values when policy guidance is missing or unknown.
- Owner assignment output must include policy-pack version, organization-model version, owner-resolution strategy, assignment-rule fingerprint, and routed counts when visible.
- Owner assignment must never silently leave review-required findings unowned; controlled P0 fixtures must expose `unownedFindings = 0`.
- Finding assembly output must include policy-pack version, source snapshot, assembly-rule fingerprint, assembled finding count, evidence-card count, redacted signal count, missing-card count, denied-action count, `rawContentExposed = false`, and `legalConclusionProvided = false` when visible.
- Finding rows may include optional `evidenceSignalCount` and `policyPackVersion`; clients must still render rows when those optional fields are absent.
- Evidence cards must expose redacted signals, policy context, owner assignment, retention status, action boundary, and audit timeline without raw source content.
- Review support output must include policy-pack version, organization-model version, visible allowed actions, visible denied actions, required reason fields, checklist items, transfer options, and escalation options when available.
- Review support must not expose raw source content, unredacted personal data, hidden permission data, legal conclusions, or deletion execution.
- Audit recording output must include policy-pack version, audit rules fingerprint, event counts, scan-linked count, finding-linked count, review-decision count, human/system counts, `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false` when visible.
- Delta scan output may include `deltaScan` with baseline scan ID, source snapshot, inventory fingerprint, baseline totals, delta fingerprint, changed/new/modified/unchanged/missing counts, carried-forward counts, reopened finding counts, warnings, `missingFilesTreatedAsDeleted = false`, `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false`.
- Missing files in a delta scan are source inventory changes only; public payloads must not imply DataSentinel deletion or proof of erasure.
- Admin metrics may include optional `aggregation` with status, input-stage basis, scan coverage, risk queue, owner backlog, review outcomes, audit evidence, delta counts, evaluation linkage, cost fields, and safety-boundary booleans. Aggregation is derived from prior workflow summaries and must not expose raw source content, legal conclusions, hidden permission data, or deletion execution.
- Evaluation may include optional `signalDetectionRulesHash`, `evaluationRulesHash`, and `qualityBasis` fields with golden dataset identity, input-stage basis, confusion matrix, scenario metrics, review-throughput context, risk-progress context, warnings, and safety-boundary booleans. Evaluation is generated from prior workflow summaries and must not expose raw source content, legal conclusions, hidden permission data, or deletion execution.

### Finding Status

`open -> assigned -> under_review -> reviewed -> closed`

Alternative terminal statuses:

- `false_positive`
- `escalated`
- `delete_candidate`
- `retained`

### Review Decisions

Allowed P0 decisions:

- `delete_candidate`
- `keep_with_reason`
- `correct_false_positive`
- `reassign_owner`
- `escalate`

Every review decision requires `reason`.

Submit guards:

- The submitted decision must be present in the actor's current review-support `availableDecisions`.
- Required review-support checklist items must be acknowledged before submission.
- `keep_with_reason` requires `retentionUntil` as the next retention review date.
- `reassign_owner` requires a transfer target.
- `escalate` requires an escalation queue.
- Repeated submissions with the same idempotency context must not create duplicate audit events or metrics.
- Denied or incomplete submissions must not create finding, audit, source, metric, or deletion state changes.
- `delete_candidate` is a review status only in P0 and must return or record `deletionExecuted = false` when that boundary is represented.

Accepted review responses may include optional `targetId`, `targetLabel`, `retentionUntil`, `idempotencyKey`, `policyPackVersion`, `permissionBoundaryFingerprint`, and `reviewSupportRulesFingerprint` fields. Audit events for accepted decisions should preserve the same policy and permission context when available.

### Audit Events

Required audit-event fields remain `auditEventId`, `eventType`, `actorId`, and `occurredAt`.

Optional P0 audit-event fields may include:

- `actorType`, `recordedAt`, `auditRecordVersion`, `objectType`, `objectId`, `action`, `outcome`, `stage`, `sourceId`, `previousState`, `resultingState`, `evidenceReferences`, `rawContentExposed`, and `legalConclusionProvided`.
- Decision context such as `decision`, `reason`, `resultingStatus`, `targetId`, `targetLabel`, `retentionUntil`, `deletionExecuted`, `policyPackVersion`, `permissionBoundaryFingerprint`, `reviewSupportRulesFingerprint`, and `idempotencyKey`.

Public audit payloads must not expose raw source content, unredacted personal data, credentials, hidden permission data, legal conclusions, or deletion execution. Human-entered audit text should be sanitized before becoming a public audit payload.

### Governance Policy Status

`draft -> validating -> pending_activation -> active -> superseded`

Rollback path:

- `active -> rolled_back`

### Task Transfer

`assigned -> transfer_pending -> assigned`

Failure path:

- `transfer_pending -> assigned` when the target rejects the task.

## Organizer Sample Source

Default demo source:

```text
https://github.com/a-klumpp/GDPR-data-samples
```

The contract represents the source as `sourceType = organizer_sample_repo` and exposes sample families as metadata. The repository content is referenced, not vendored.

## Mock Payloads

Frontend agents should begin with:

- `contracts/mocks/adminMetrics.json`
- `contracts/mocks/auditEvents.json`
- `contracts/mocks/evaluationLatest.json`
- `contracts/mocks/findingDetail.json`
- `contracts/mocks/governanceConfig.json`
- `contracts/mocks/myFindings.json`
- `contracts/mocks/permissionBoundary.json`
- `contracts/mocks/reviewDecision.json`
- `contracts/mocks/reviewSupport.json`
- `contracts/mocks/scanStatus.json`
- `contracts/mocks/sources.json`

Mocks are contract fixtures. They are not production seed data.

Scan mocks may include optional `fileInventory`, `contentExtraction`, `signalDetection`, `contextRisk`, `ownerAssignment`, `findingAssembly`, `reviewSupport`, and `pipelineStages` fields. These fields summarize internal processing and are safe for public UI because they expose counts, hashes, methods, policy-pack version, organization-model version, warnings, and redaction boundaries rather than raw source content.

Admin metrics mocks may include optional `detectedSignals`, `redactedSignals`, `findingsWithSignals`, and `aggregation`, and evaluation mocks may include optional `signalDetectionRulesHash` and `adminMetricsRulesHash`. These fields are forward-compatible management evidence for the signal-detection and admin-metrics aggregation stages.

Evaluation mocks may include optional `evaluationRulesHash` and `qualityBasis`. These fields are forward-compatible measurement evidence for the evaluation-metrics generation stage.

## Breaking Changes

Breaking changes require a documented contract version bump:

- Removing a field currently marked required.
- Renaming a field.
- Changing an ID, date, boolean, object, array, or number into another type.
- Closing an enum-like string so unknown values fail.
- Changing endpoint semantics.
- Changing review or scan state transitions.
