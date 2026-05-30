# Backend Post-Source Stage Details

This companion document expands the stage summary in `docs/design/backend-post-source-execution-plan.md`. It remains a planning artifact only; it does not approve implementation code, runtime dependencies, production integrations, or public contract changes.

## Step 1: Full Scan Orchestration

Purpose: accept a connected sample source and create a scan record that can move through queued, running, completed, failed, and cancelled states.

Primary contract surface:

- `POST /api/scans/full`
- `GET /api/scans/{scanId}`
- `GET /api/scans/{scanId}/summary`

Inputs:

- `sourceId`
- `X-Actor-Id`
- `Idempotency-Key` when available
- Active policy-pack version
- Source adapter readiness from governance config

Outputs:

- Scan ID, scan type, progress, counts, duration, throughput, trace ID, and warnings when partial data exists.

Exit criteria:

- A scan can be represented as queued, running, completed, failed, or cancelled.
- Duplicate scan-start requests with the same idempotency key do not create conflicting demo scans.
- Scan status can be read without running the full pipeline synchronously.

## Step 2: Source Inventory and Extraction Planning

Purpose: convert source contents into file candidates and extraction outcomes without leaking raw content through the public contract.

Primary contract surface:

- `GET /api/scans/{scanId}`
- `GET /api/admin/metrics`
- Internal boundary only; no P0 public extraction endpoint.

Inputs:

- Connected source metadata, sample family labels, file path, size, modified timestamp, and stable file fingerprint.

Outputs:

- File inventory count, extraction status, recoverable warnings, and redacted or derived evidence candidates only.

Exit criteria:

- Unreadable or unsupported files can produce warnings without breaking the scan.
- Raw extracted text is not exposed through public responses.
- File fingerprints are stable enough to support reproducibility and delta scans.

## Step 3: Deterministic Signal Detection

Purpose: identify GDPR-relevant evidence candidates through deterministic detectors before any AI-assisted classification or explanation.

Primary contract surface:

- `GET /api/findings`
- `GET /api/findings/{findingId}`

Inputs:

- Extracted text or structured file metadata inside the backend boundary.
- Detector rules version or hash.
- Policy-pack evidence requirements.

Outputs:

- Detector signals with type, detector name, confidence, redacted snippet, and location when available.
- Personal data type labels such as `email`, `employee_id`, `billing_address`, `iban_like`, `signature`, or `access_role`.

Exit criteria:

- Every created finding has at least one evidence signal.
- Snippets are redacted before crossing the public API boundary.
- Detector output can be fingerprinted for reproducibility.

## Step 4: Context Classification and Risk Planning

Purpose: turn signals into finding context, risk level, risk score, retention status, and a plain-language explanation without producing a legal conclusion.

Implemented P0 slice: `docs/design/context-risk-judgment.md` defines the deterministic scan-level context/risk judgment stage that follows extraction and signal detection.

Primary contract surface:

- `GET /api/findings`
- `GET /api/findings/{findingId}`
- `GET /api/governance/policy-packs/active`

Inputs:

- Signals, file family or inferred document category, last modified timestamp, and active policy-pack guidance.

Outputs:

- `contextCategory`, `riskLevel`, `riskScore`, `retentionStatus`, `riskExplanation`, and `policyContext`.
- Optional scan-level `contextRisk` summary with policy-pack version, risk-rule fingerprint, context/risk counts, retention-review count, human-review count, and `legalConclusionProvided = false`.

Exit criteria:

- Risk output explains evidence and policy guidance, not a hard legal conclusion.
- Retention status can be `unknown` or neutral when metadata is insufficient.
- Unknown context categories remain renderable by tolerant clients.

## Step 5: Owner Routing

Purpose: assign each finding to an accountable person or escalation path.

Implemented P0 slice: `docs/design/owner-routing-assignment.md` defines the deterministic scan-level owner-routing stage that follows context/risk judgment.

Primary contract surface:

- `GET /api/findings`
- `GET /api/findings/{findingId}`
- `GET /api/findings/{findingId}/review-support`
- `GET /api/governance/config`

Inputs:

- File metadata, source-level `masterOfDataUserId`, organization model, direct owner signals when available, and escalation rules.

Outputs:

- Owner object with user ID, display name, email, assignment type, fallback assignment, or escalation options.
- Optional scan-level `ownerAssignment` summary with policy-pack version, organization-model version, owner-resolution strategy, assignment-rule fingerprint, routed counts, escalation count, and unowned count.

Exit criteria:

- A finding is never silently unowned.
- Owner assignment type explains whether the owner is direct, fallback, delegated, or escalation-based.
- Owner routing creates or contributes to an audit-visible event when the finding becomes assigned.
- Controlled P0 fixtures keep owner routing deterministic, zero-cost, and free of production directory or notification integrations.

## Step 6: Finding Assembly and Evidence Card

Purpose: assemble a contract-compatible finding detail view from internal scan, evidence, risk, owner, policy, and audit data.

Implemented P0 slice: `docs/design/finding-assembly-evidence-card.md` defines the deterministic scan-level finding-assembly stage that follows owner routing.

Primary contract surface:

- `GET /api/findings`
- `GET /api/findings/{findingId}`

Inputs:

- Scan ID, file metadata, signals, context and risk, owner, policy context, and existing audit events.

Outputs:

- Finding list rows and detail views with redacted evidence, signals, risk explanation, owner assignment, retention status, actions, and audit timeline.

Exit criteria:

- The finding detail can support the P0 evidence card without additional endpoint assumptions.
- Empty audit timelines and optional fields remain valid.
- Denied actions are visible when the permission boundary provides them.

## Step 7: Review Support and Permission Boundary

Purpose: make the reviewer's choices explicit before the reviewer acts.

Implemented P0 slice: `docs/design/review-support-permission-boundary.md` defines the deterministic scan-level review-support stage that follows finding assembly.

Primary contract surface:

- `GET /api/users/me/permissions`
- `GET /api/findings/{findingId}/review-support`

Inputs:

- Actor ID, finding status, owner assignment, active policy pack, organization model, and delegation rules.

Outputs:

- Allowed actions, denied actions and reasons, checklist, available decisions, required reason fields, transfer options, and escalation options.
- Optional scan-level `reviewSupport` summary with policy-pack version, organization-model version, support-rule fingerprint, supported finding count, decision count, checklist count, transfer count, escalation count, denied action count, and no-legal-conclusion boundary.

Exit criteria:

- A reviewer can see available and unavailable actions before submit.
- Required reason fields are known before submit.
- Permission denial can be returned as problem details if the actor still attempts a denied action.
- Controlled P0 fixtures keep review support deterministic, zero-cost, and free of production authorization, directory, notification, and deletion integrations.

## Step 8: Human Review Command Handling

Purpose: record human review decisions as accountable state changes.

Primary contract surface:

- `POST /api/findings/{findingId}/review`
- `GET /api/findings/{findingId}`
- `GET /api/audit/events`

Inputs:

- Actor ID, finding ID, decision, reason, idempotency key when available, policy-pack version, and permission context.

Outputs:

- Resulting finding status, review decision record, audit event, and updated available or denied actions.

Exit criteria:

- `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate` can be represented.
- Every decision requires a human actor and reason.
- Real deletion is not executable in P0.
- Duplicate review submission with the same idempotency key does not create conflicting audit events.

## Step 9: Audit Event Logging

Purpose: preserve the system and human story of the finding lifecycle.

Implemented P0 slice: `docs/design/audit-event-recording.md` defines the deterministic audit-event recording stage that connects scan lifecycle events, owner routing, finding assembly, finding timelines, and human review decisions.

Primary contract surface:

- `GET /api/audit/events`
- Finding detail `auditTimeline`

Inputs:

- Scan start, scan completion, finding creation, owner assignment, task view when available, review decisions, policy context, and actor context.

Outputs:

- Audit events with actor, actor type, timestamp, event type, action, object, previous state, resulting state, summary, evidence references, finding ID when applicable, scan ID when applicable, and policy context when applicable.

Exit criteria:

- Every review decision creates an audit event.
- Audit events never expose raw sensitive content.
- Audit events preserve enough context to explain why a finding reached its current status.

## Step 10: Delta Scan Planning

Purpose: represent ongoing governance by scanning changed files after a baseline full scan.

Primary contract surface:

- `POST /api/scans/delta`
- `GET /api/scans/{scanId}`
- `GET /api/admin/metrics`
- `GET /api/evaluation/runs/latest`

Inputs:

- Previous completed scan baseline, file fingerprints, modified timestamps, and current source inventory.

Outputs:

- Delta scan ID, changed-file counts, new, changed, unchanged, and missing file handling, and updated findings where changed evidence or metadata affects risk, owner, or retention status.

Exit criteria:

- A delta scan can represent changed-file-only processing.
- Unchanged files are not treated as newly scanned findings unless their policy context changes.
- Missing files do not imply deletion by DataSentinel; they are represented as source inventory changes.

## Step 11: Admin Metrics Aggregation

Purpose: make backend progress, risk, and backlog visible as product evidence.

Primary contract surface:

- `GET /api/admin/metrics`
- `GET /api/scans/{scanId}/summary`

Inputs:

- Scan status, finding statuses, risk levels, review backlog, retention status, and evaluation summary when available.

Outputs:

- Scanned files, flagged files, scanned volume, progress, scan time, review backlog, high-risk count, retention-overdue count, and throughput.

Exit criteria:

- Metrics can be partially available while a scan is running.
- `meta.partial = true` and warnings explain incomplete metrics.
- Admin metrics match the terms used in `ACCEPTANCE.md`.

## Step 12: Evaluation Run Planning

Purpose: prove scan quality and operational cost are measurable.

Primary contract surface:

- `GET /api/evaluation/runs/latest`

Inputs:

- Dataset hash, scanner version, detector rules hash, config hash, policy-pack version, finding fingerprints, and ground-truth fixture or deterministic mock values for P0.

Outputs:

- Precision, recall, F1, reproducibility, throughput, and resource intensity.

Exit criteria:

- Evaluation can be shown even if the first implementation uses deterministic mock values.
- Reproducibility ties back to dataset, detector rules, configuration, and policy-pack version.
- Resource intensity is explicit about memory, CPU, model calls, and estimated cost.
