# API Contract

## Purpose

This contract lets frontend and backend agents work in parallel without blocking each other. It is intentionally broad and tolerant for the hackathon prototype while still giving stable shapes for UI, backend, mocks, and tests.

Source of truth:

- Machine-readable contract: `contracts/openapi.yaml`.
- Mock payloads: `contracts/mocks/`.
- Design rationale: `docs/design/frontend-backend-delivery-contract.md`.
- Adaptive governance rationale: `docs/design/adaptive-governance-review-control.md`.
- Workspace admin rationale: `docs/design/workspace-admin-permission-system.md`.

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
- Authenticated prelaunch requests should rely on the first-party HttpOnly session cookie created by the auth callback. SQLite-backed prelaunch Sources, scans, findings, audit events, metrics, and evaluation state are scoped to that session user. `X-Actor-Id` remains a development compatibility header and is not authentication.
- Workspace requests use the first-party account identity plus explicit Workspace membership. Authentication alone does not grant Workspace access.

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
| `GET` | `/api/auth/providers` | List configured Google and GitHub login providers without secrets. |
| `GET` | `/api/auth/login/{provider}` | Start backend-owned OAuth login for `google` or `github`. |
| `GET` | `/api/auth/callback/{provider}` | Complete provider callback, create a first-party session, and redirect back to the app. |
| `GET` | `/api/auth/session` | Read current first-party session and safe user profile. |
| `POST` | `/api/auth/logout` | Revoke the current first-party session and clear the session cookie. |
| `GET` | `/api/workspaces` | List Workspaces visible to the current account and any legacy account-targeted pending invitations. |
| `POST` | `/api/workspaces` | Create a Workspace and add the creator as `workspace_owner` and `workspace_admin`. |
| `POST` | `/api/workspaces/current` | Switch the signed-in account's current Workspace context. |
| `GET` | `/api/workspaces/current/admin` | Read Workspace admin summary, groups, members, invitations, permission boundary, and charts for the current Workspace context. |
| `DELETE` | `/api/workspaces/{workspaceId}` | Soft-delete a Workspace after exact-name confirmation by the current Workspace owner. |
| `POST` | `/api/workspaces/{workspaceId}/owner-transfer` | Transfer Workspace owner authority to an active member. |
| `POST` | `/api/workspaces/{workspaceId}/groups` | Create a Workspace group with a name, description, and explicit permission set. |
| `PATCH` | `/api/workspaces/{workspaceId}/groups/{groupId}` | Update a Workspace group's visible name, description, and permissions. |
| `DELETE` | `/api/workspaces/{workspaceId}/groups/{groupId}` | Delete a non-admin Workspace group and remove its references from members and pending invite links. |
| `PATCH` | `/api/workspaces/{workspaceId}/members/{membershipId}` | Update a Workspace member's explicit group assignments. |
| `DELETE` | `/api/workspaces/{workspaceId}/members/{membershipId}` | Remove an active Workspace member from the Workspace. |
| `POST` | `/api/workspaces/{workspaceId}/invitations` | Generate a Workspace invitation link for a group set. |
| `POST` | `/api/workspaces/invitations/{invitationId}/accept` | Accept a pending Workspace invitation link as the current signed-in account. |
| `GET` | `/api/integrations/google-drive/picker-config` | Read session-protected Google Drive Picker browser setup state without secrets. |
| `GET` | `/api/sources` | List configured sources. |
| `POST` | `/api/sources` | Create a mock, local, direct-link, or Google Drive selected source. |
| `DELETE` | `/api/sources/{sourceId}` | Delete a DataSentinel source registration without deleting external source files. |
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

### Account Session

Provider login uses backend authorization-code flows. Provider client secrets and provider tokens must stay server-side. The browser receives only a first-party HttpOnly session cookie and safe profile fields from `/api/auth/session`.

`signed_out -> auth_starting -> provider_redirected -> callback_validating -> session_active`

Failure paths:

- `auth_starting -> auth_failed` when the provider is unknown, disabled, or missing credentials.
- `callback_validating -> auth_failed` when provider error, missing code, state mismatch, token exchange failure, or missing stable provider user ID occurs.
- `session_active -> signed_out` when logout is accepted or the session expires.

Auth payloads:

- Provider list exposes `provider`, `label`, `configured`, and `loginUrl`.
- Session read exposes `authenticated`, optional `user`, and optional `expiresAt`.
- User profile exposes local `userId`, `provider`, `providerSubject`, `displayName`, optional `email`, and optional `avatarUrl`.
- Provider access tokens, refresh tokens, client secrets, auth state, and PKCE verifier are never returned.

Account and Workspace-scoped state:

- When `DATASENTINEL_AUTH_REQUIRED=true`, protected SQLite-backed routes without an active Workspace resolve the owner scope from the first-party session `userId`.
- When the account has an active current Workspace, Source list/mutation routes, scan routes, finding routes, audit, metrics, and evaluation resolve the owner scope from `workspace:{workspaceId}` instead of the account.
- Switching Workspace context changes the operational owner scope for subsequent Source, scan, finding, audit, metric, and evaluation reads and writes.
- Source list/mutation routes, scan routes, finding routes, audit, metrics, and evaluation return only the current account or current Workspace state.
- Cross-account source and finding identifiers behave as not found or as the current account's empty state.
- Request payloads and compatibility headers cannot override the owner scope.

### Workspace Membership and Invitations

Accounts and Workspaces are separate. A newly created account starts without Workspace membership unless it accepts an invitation link or is represented by seeded demo membership. Workspace groups carry permissions inside a Workspace; they do not grant production tenant, provider, source-file deletion, or legal-advice powers.

Workspace creation:

- `POST /api/workspaces` accepts `name` and optional `description`.
- The creator becomes an active member of the new Workspace with both `workspace_owner` and `workspace_admin`.
- The new Workspace becomes the creator's current Workspace context.
- The new Workspace receives the default P0 group definitions for owner, admin, privacy reviewer, data steward, and auditor.
- Workspace creation does not create a production tenant, external directory, source connector, billing object, email domain, or deletion capability.

Workspace switching:

- `POST /api/workspaces/current` accepts `workspaceId`.
- The target Workspace must exist and the current account must have an active membership in it.
- Successful switching stores only the current Workspace selection for the account and updates subsequent operational reads to the selected Workspace scope.
- Switching does not copy sources, findings, scan state, metrics, audit events, invitations, members, or groups between Workspaces.
- Unknown or non-member Workspace IDs return problem details and leave the previous selection unchanged.

Workspace payloads:

- `WorkspaceDirectory` exposes visible Workspaces, current Workspace ID when membership exists, legacy account-targeted pending invitations when present, and whether a Workspace is required before using the console.
- `WorkspaceAdminSummary` exposes the current Workspace, current membership, permission catalog, groups, members, invitations, Workspace permission boundary, and chart data.
- `WorkspaceGroup` exposes group ID, Workspace ID, visible name, description, explicit permissions, and member count.
- `WorkspaceInvitation` exposes invitation status, invite path, invited groups, inviter, creation time, and expiry time. Provider tokens, auth secrets, and hidden directory data are never returned.

Workspace permission actions are open strings, but group mutation accepts only the exposed P0 permission catalog. Known P0 actions include `manage_workspace_ownership`, `view_workspace_admin`, `invite_workspace_members`, `manage_workspace_members`, `manage_workspace_groups`, `view_workspace_audit`, `view_workspace_metrics`, `view_assigned_findings`, `view_review_support`, `review_findings`, `view_owned_sources`, `view_governance`, and denied `execute_real_deletion`.

Workspace group state:

`group_defined -> group_updated -> group_deleted`

Group command guards and side effects:

- Group creation, update, and deletion require `manage_workspace_groups`.
- Group creation and update reject missing names, duplicate names within a Workspace, and unknown permissions.
- Updating a group preserves `groupId`, so memberships and invite links continue referencing the same group.
- The `workspace_owner` group cannot be deleted and must retain `manage_workspace_ownership`, `view_workspace_admin`, and `manage_workspace_members`.
- The `workspace_admin` group cannot be deleted and must retain `view_workspace_admin` and `manage_workspace_groups`.
- Deleting a non-admin group removes that `groupId` from active memberships and invitation group lists.
- Pending invite links with no remaining groups after deletion become `revoked`.

Workspace member state:

`member_active -> member_groups_updated -> member_removed`

Member command guards and side effects:

- Member group updates and member removal require `manage_workspace_members`.
- Adding or removing `workspace_owner` from a member requires `manage_workspace_ownership`.
- Member group updates require at least one valid group from the target Workspace.
- Member group updates and member removal must leave at least one active member assigned to `workspace_owner`.
- Member group updates and member removal must leave at least one active member assigned to `workspace_admin`.
- A Workspace admin cannot remove their own active membership through the member removal command.
- Removing a member changes their membership status to `removed` and clears that account's selected Workspace if it pointed at the removed Workspace.

Workspace owner state:

`workspace_active -> owner_transferred -> workspace_active -> workspace_deleted`

Owner command guards and side effects:

- Owner transfer and Workspace deletion require `manage_workspace_ownership`.
- `POST /api/workspaces/{workspaceId}/owner-transfer` accepts `membershipId` for an active member in the same Workspace.
- A successful owner transfer assigns `workspace_owner` and `workspace_admin` to the target member and removes `workspace_owner` from the previous active owner.
- `DELETE /api/workspaces/{workspaceId}` accepts `workspaceName`; it must exactly match the current Workspace name.
- Workspace deletion is a soft delete of the local Workspace record. It removes active memberships, revokes pending invitations, clears current Workspace selections for affected accounts, and does not delete external source files or production tenant resources.

Invitation state:

`workspace_unassigned -> invitation_pending -> workspace_member_active`

Failure paths:

- Non-admin invitation creation returns `403` problem details and changes no state.
- Empty group list returns `422` problem details and changes no state.
- Invitation creation rejects `workspace_owner`; Owner authority must be transferred by the owner-transfer command instead of invite link.
- Each invitation creation generates a new pending link unless validation fails.
- Expired, revoked, already accepted, or already-member invitation acceptance returns problem details and changes no state.

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
    { "tier": "ocr", "provider": "local_tesseract", "mode": "local", "status": "local_available", "atlasStages": [2] },
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
- P0 accepts full-scan start for the controlled `mock_ready` organizer sample source, connected local prelaunch sources, connected direct HTTPS file links, and connected Google Drive selected sources.
- `google_drive_selection` scans require `authorization.googleDriveAccessToken` in the scan request. The token is a short-lived per-scan value and must not be stored by the server.
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

## Prelaunch Source Inputs

Source records may include optional `config` for connector-specific metadata:

- `remote_file_link` stores `config.url` as a direct HTTPS file URL. The backend validates that the URL is HTTPS, has no embedded credentials, resolves to public IP addresses, is not a Google Drive or Google Docs share page, and points to supported text-like content, a PDF text layer, Office Open XML content, supported image content, supported transcript content, or recognized raw video media. Extractable files must stay within the prelaunch size limit; raw video media is reported as hard/OCR-deferred until an approved processor exists.
- `google_drive_selection` stores `config.items`, an array of Google Picker selected item metadata such as `id`, `name`, `mimeType`, and optional `url`. The backend uses this metadata only with a per-scan `authorization.googleDriveAccessToken`.
- `local_repo` stores `config.rootPath` for host-mounted folders that pass the configured allowed-root policy.

`DELETE /api/sources/{sourceId}` removes only the DataSentinel source registration row. It must not delete, mutate, or revoke any file in Google Drive, a remote HTTPS location, or a host-mounted source directory.

`GET /api/integrations/google-drive/picker-config` requires the first-party session cookie when `DATASENTINEL_AUTH_REQUIRED=true` and returns browser-safe Picker setup state:

```json
{
  "data": {
    "configured": true,
    "clientId": "public-oauth-client-id",
    "apiKey": "public-picker-api-key",
    "appId": "google-cloud-project-number",
    "scopes": {
      "files": "https://www.googleapis.com/auth/drive.file",
      "folders": "https://www.googleapis.com/auth/drive.readonly"
    },
    "missing": []
  }
}
```

The endpoint may return `configured = false` with `null` browser setup fields and a `missing` list. It must never return Google client secrets, GitHub credentials, provider access tokens, refresh tokens, auth transaction state, raw source content, or unredacted personal data.

Prelaunch source scans read raw source content only inside the scan process. Public payloads may expose source metadata, counts, warnings, redacted snippets, findings, metrics, and audit events; they must not expose raw file bodies, page images, provider tokens, refresh tokens, client secrets, legal conclusions, or deletion execution.

`contentExtraction` may include optional `recognitionDifficulty`, `formatCounts`, `aiAssistanceUsed`, and `modelCalls` fields. Difficulty tiers are:

- `easy`: direct UTF-8 text-like extraction.
- `moderate`: deterministic structured extraction such as PDF text layers, DOCX/XLSX/PPTX Office Open XML text, and VTT/SRT video transcript text.
- `hard`: image OCR, OCR-deferred, raw video media, or richer-parser-needed inputs.
- `unsupported`: unknown, unsafe, over-limit, malformed, or unsupported formats.

Normal deterministic source scans must keep `aiAssistanceUsed = false` and `modelCalls = 0`; OpenRouter remains only an explicit assistive boundary for redacted evidence.

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

Prelaunch hosts should set `DATASENTINEL_ENABLE_DEMO_FIXTURES=false` so `/api/sources`, `/api/findings`, `/api/audit/events`, metrics, and evaluation begin empty and populate only from configured local sources and user actions.

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
