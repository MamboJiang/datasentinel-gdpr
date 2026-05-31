# Frontend Console Contract

## Purpose

This document defines the functional contract for the internal DataSentinel product console. It tells frontend implementers what the console must support for P0 acceptance without prescribing visual design, component styling, layout composition, animation direction, or implementation architecture.

The console is the internal workspace simulation for a GDPR-relevant discovery workflow. It must make findings measurable, explainable, owner-routed, human-reviewed, audit-ready, and safe by default.

## Contract Sources

The console must stay aligned with `ACCEPTANCE.md`, `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, `contracts/mocks/`, `docs/PROJECT_CONTEXT.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, `docs/GOVERNANCE_CONFIG.md`, `docs/EVALUATION.md`, `docs/SECURITY_NOTES.md`, and the design notes under `docs/design/` for scan start, inventory/extraction, deterministic signal detection, context risk, owner routing, finding assembly, review support, human review, audit recording, incremental delta scan, account-menu utility actions, local language preference, sidebar resize/collapse, and file review.

## Scope

In scope:

- Internal shell, navigation, dashboard, sources, scan pipeline, findings, finding detail, file review, review dialog, audit, evaluation, governance, permissions, notifications, and state handling.
- Mock-backed role and actor simulation through seeded users or `X-Actor-Id`.
- Contract-tolerant rendering from mock payloads and future backend responses.
- Loading, empty, error, partial-data, warning, unknown-value, and denied-action states.
- Privacy, safety, accessibility, and responsive obligations required for final product acceptance.

Out of scope:

- Public homepage requirements, which are defined in `docs/WEBSITE_HOMEPAGE_CONTRACT.md`.
- Production authentication, authorization, Microsoft Graph, OAuth, tenant, source connector, parser, OCR, AI, queue, database, or deletion integration.
- Final visual design system, exact component hierarchy, CSS implementation, chart library, animation direction, or copywriting polish.

## Non-Negotiable Boundaries

- Developer-facing repository documents, engineering instructions, and code comments must be English; user-facing console text may be localized through reviewed frontend dictionaries.
- The console must not expose raw extracted text, full file bodies, page images, or unredacted personal data.
- The console must not execute, imply, or visually celebrate real deletion.
- `delete_candidate` is only a human review status in P0.
- The console must not claim full GDPR compliance or provide legal advice.
- Policy guidance and human accountability must be shown instead of hard-coded legal conclusions.
- Permission boundaries must be visible before review submission.
- Denied actions must show denial reasons when the contract provides them.
- Unknown fields must be ignored; unknown enum-like values must render neutrally.
- Missing optional fields, `null` optional objects, empty arrays, partial payloads, and numeric metrics that are `null` while work is running must not break rendering.

## Actor and Role Simulation

P0 role handling is a demo simulation, not production authentication. Role switching, if exposed, must refresh allowed actions, denied actions, visible scopes, review support, and finding visibility.

| Perspective | Required console behavior |
| --- | --- |
| IT administrator or privacy admin | Inspect sources, start allowed scans, view dashboard metrics, inspect governance, audit, and evaluation. |
| Master of Data or department steward | View assigned findings, review support, permission boundaries, and allowed review decisions. |
| Direct owner | View findings in visible scope and act only within assigned responsibility. |
| DPO or legal reviewer | Inspect escalated work and audit context without receiving automated legal conclusions. |
| Auditor or compliance reviewer | Inspect audit, evaluation, and governance evidence in a read-oriented workflow. |
| Employee or file owner | See only visible scopes and never gain admin or cross-owner access. |
| Unknown or missing actor | Receive neutral denied or unavailable states without privileged data leakage. |

## Route Contract

The public root route `/` belongs to the homepage. The internal console starts at `/dashboard`.

| Route | Surface |
| --- | --- |
| `/dashboard` | Admin dashboard and latest scan overview. |
| `/sources` | Source connector and source readiness. |
| `/findings` | Findings list. |
| `/findings/:findingId` | Finding detail and evidence card. |
| `/audit` | Global audit event view. |
| `/evaluation` | Evaluation metrics. |
| `/governance` | Governance configuration and permission-boundary inspection. |
| `/account` | Simulated actor, workspace, and permission-boundary account settings. |
| `/feedback` | Local-only prototype feedback note surface. |
| `/changelog` | P0 prototype change log. |
| `/help` | Task-oriented console help. |
| `/docs` | Local repository documentation map. |
| `/status` | Mock-backed platform status surface. |
| `/plan` | Prototype plan boundary without billing or tenant onboarding. |
| `/session` | Session-boundary page for simulated log-out behavior. |

## App Shell Contract

The internal shell must provide current page title, notifications or status indicators, top-left workspace context, bottom-left account controls, sidebar collapse/expand, desktop sidebar resize by pointer or keyboard separator, active-route indication, route navigation, keyboard-accessible menus, focus-safe close behavior, and responsive readability. Sidebar resize must collapse when dragged below the configured threshold and cap expansion at the configured maximum width. Account menu controls must either navigate to a concrete local utility route or perform a clearly local UI action. Theme switching and language preference may use local browser state. Language preference uses static frontend dictionaries for user-facing UI copy; developer-facing docs, engineering notes, and code comments remain English-only. Feedback must remain local-only in P0. Log out, plan, and status controls must expose prototype boundaries instead of production authentication, billing, tenant, support, monitoring, or translation-service behavior. The shell must not mix public homepage navigation into the internal workspace shell or hide account, workspace, or permission context.

## Shared Data Contract

Every console surface that consumes API or mock data must handle the standard envelope: `data`, `meta`, and optional `pagination`. It must render `meta.contractVersion`, `meta.generatedAt`, `meta.traceId`, `meta.partial`, `meta.warnings`, and `application/problem+json` errors in an appropriate user-facing or diagnostic way. Scan start and review submission must preserve idempotency behavior when the backend or mock workflow provides it.

## Surface Requirements

| Surface | Must cover | Safety and behavior requirements |
| --- | --- | --- |
| Dashboard | Default organizer source readiness; full-scan action for controlled `mock_ready` source; baseline-aware delta action; latest scan status/type; progress; scanned files; flagged files; scanned volume; duration; throughput; review backlog; high-risk count; retention-review or overdue count; human-review-required count; owner routing; pipeline stages; inventory/extraction; signal detection; context/risk; finding assembly; review support; audit recording; delta baseline and changed-file counts; aggregate management indicators; active policy version; evaluation and resource intensity. | Full and delta scans must use explicit `sourceId`; delta scans require a completed selected-source baseline; not-ready sources cannot create scans or audit events; duplicate starts cannot create conflicting records; aggregate metrics must show owner completion, risk queue, audit evidence, metric basis, and cost when available; raw content, legal conclusions, paid model usage, and deletion instructions must not appear. |
| Sources | Source ID/reference, name, type, status, root label, Master of Data owner, reference URL, sample families, adapter readiness, source-specific scan action, connection test when available, source-registration deletion, and delta scan start when a baseline can be represented. | Source-row scan must target the selected `sourceId`; the first source must not be hard-coded; missing, unreadable, or not-ready sources cannot create downstream scan, finding, review, audit, or evaluation state; source-registration deletion must not claim or trigger source-file deletion. |
| Scan pipeline | `source_ready`, optional `comparing_delta_baseline`, `inventorying_files`, `extracting_content`, `detecting_signals`, `judging_context_risk`, `assigning_owner`, `assembling_findings`, `preparing_review_support`, `recording_audit_events`, and `completed` when present. | Stages must support pending, running, completed, warning, failed, unavailable, counts, warnings, and unknown-stage fallback. Ordering must not imply delta comparison before source readiness or context/risk, owner routing, review support, or audit before upstream evidence stages. |
| Inventory and extraction | Source snapshot ID, inventory fingerprint, candidate files, fingerprinted files, skipped files, total bytes, permission snapshots, sample-family distribution, extraction fingerprint, processed files, successful files, warning files, unsupported files, OCR-deferred files, redacted evidence candidates, extraction methods, and `rawContentExposed = false`. | Unsupported and OCR-deferred files are recoverable warnings, not hidden failures or blockers. No public extraction endpoint is required. |
| Deterministic signal detection | Detector rules version/hash, policy-pack evidence requirements, evaluated evidence candidates, detected/redacted signal counts, findings-with-signals count, signal-type counts, warnings, and `rawContentExposed = false`. | Runs after extraction and before context/risk. It must expose redacted evidence only, not raw extracted text, file bodies, page images, detector secrets, legal conclusions, or deletion execution. |
| Findings list | Finding ID, scan ID, file name, safe source path/reference, risk level, score, context category, personal data types, retention status, recommended action, status, owner, assignment type, policy context, available actions, denied actions, pagination, and filters for scan, owner, risk, and status when available. | Empty, loading, partial, error, unknown risk/status, and missing optional owner fields must render. Raw sensitive values must not appear. |
| Finding detail | File context, risk, context category, personal data types, retention status, recommendation, status, policy context, owner assignment, file metadata, redacted signals, detector, confidence, location/fallback, risk explanation, available actions, denied actions, and audit timeline. | It must open file review from header or evidence, open review only after support/boundary context, tolerate empty audit timelines and unknown signals, and avoid legal conclusions. |
| File review editor | Open from finding detail, select first evidence by default, open from a specific evidence card, switch anchors, focus or highlight redacted preview regions, show fallback location, and close without changing state. | Only redacted snippets, masked values, location labels, and safe metadata may appear. PDF, DOCX, XLSX, CSV, TXT, Markdown, and unknown formats must have locator or fallback behavior. |
| Review support | Finding ID, actor ID, policy-pack version, plain-language summary, available decisions, reason requirements, checklist, transfer options, escalation options, permission boundary, allowed actions, denied actions, and visible scopes. | Support must be finding-specific when data allows it. Decisions include `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate`. |
| Review decision | Available decision validation, actor, non-empty reason, checklist acknowledgement when required, retention review date for keep-with-reason when required, supported transfer target for reassignment, and supported queue for escalation. | Accepted decisions create one review record and one audit event, update visible state and metrics when available, and preserve policy/permission context. Rejected decisions leave finding, audit, metrics, and source state unchanged. `delete_candidate` never mutates source files. |
| Audit | Event ID, type, actor, timestamp, scan/finding IDs, object details when available, previous/resulting state, outcome, reason, policy version, permission context, evidence reference count, summary, filtering, pagination, and consistency between global audit and finding timeline. | Human-entered text must be sanitized before display. Audit must not contain raw sensitive content. |
| Evaluation | Evaluation run, scan ID, dataset hash, scanner version, detector rules hash, signal-detection rules hash, context-risk hash, owner-assignment hash, finding-assembly hash, review-support hash, human-review hash, audit rules fingerprint, admin-metrics hash, config hash, finding fingerprint, precision, recall, F1, reproducibility, throughput, peak memory, CPU seconds, model calls, and estimated cost when available. | P0 must show zero model calls and zero estimated paid-service cost when provided. Mock values must not be represented as production-certified quality. Partial evaluation must show warnings. |
| Governance | Config ID, active policy pack, version, status, jurisdiction tags, effective dates, retention rules, risk guidance, evidence requirements, escalation paths, review decisions, organization model, owner-resolution strategy, org units, Master of Data fallback, delegation rules, source adapters, readiness, change controls, `realDeletionAllowed = false`, and change previews. | Governance actions must show denied reasons when unavailable. Historical policy context must remain visible in audit/finding views. Legal rules must not appear as hard-coded scanner logic. |
| Permission boundary | Actor ID, roles, allowed actions, denied actions, denial reasons, and visible scopes. | Boundaries must be shown before action, refreshed when actor context changes, and enforced on denied submissions. Denied actions should not be silently hidden when reasons exist. |

## Incremental Delta Scan Contract

When the contract provides delta data, the console must show baseline identity, changed/new/modified/unchanged/missing counts, processed changed files, carried-forward files or findings, reopened findings, and warnings. Missing files must be rendered as source inventory changes, not deletion. Delta state must preserve `rawContentExposed = false`, `legalConclusionProvided = false`, `missingFilesTreatedAsDeleted = false`, and `deletionExecuted = false` when those fields are available.

## Notifications and Status

The console should surface scan started, scan completed, scan rejected, partial data available, recoverable warning, review recorded, review rejected, audit event created, governance preview ready, and backend/mock unavailable states. Notifications must not include raw sensitive content and must not replace audit records.

## Error and Partial-State Contract

Every major surface must support loading, empty, partial data, recoverable warning, permission denied, validation error, not found, conflict or duplicate command, backend unavailable, and mock-backed fallback states. Problem details should show a concise user-facing message and preserve `traceId` for troubleshooting.

## Accessibility and Responsive Contract

The console must support keyboard navigation for routes, menus, dialogs, review actions, and file review; focus management for dialogs and overlays; visible focus states; screen-reader-readable labels for commands and statuses; reduced-motion compatibility; readable text at supported viewport sizes; and controls whose labels do not overflow.

The console must remain usable on desktop and mobile. Navigation, review actions, evidence cards, file review fallback, metrics, long file names, paths, policy versions, and reasons must remain reachable and readable without overlap.

## Acceptance Checklist

The console satisfies this contract when:

- Each implemented route consumes only fields documented in `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, `contracts/mocks/`, or tolerated optional fields.
- Dashboard, sources, findings, finding detail, file review, review, audit, evaluation, governance, permissions, and shared state surfaces are available or explicitly deferred for the current milestone.
- The default flow can run from controlled source to full scan, aggregate metrics, finding detail, review decision, audit event, delta representation, and evaluation metrics.
- Every review decision requires a human actor and reason.
- Denied actions are visible with reasons.
- Raw sensitive content is not exposed.
- Real deletion is not available.
- Legal conclusions and full-compliance claims are absent.
- Unknown, empty, partial, loading, and error states are covered.
- Role simulation does not leak cross-scope data.
- Account menu actions are usable, documented as prototype-safe, and do not imply production authentication, billing, support, or monitoring integration.
- Account menu language preference is keyboard-accessible, persists locally, updates core user-facing UI copy from local dictionaries, and does not call external translation services in P0.
- Desktop sidebar resize and drag-to-collapse work without overlapping the content area; mobile keeps the slide-in navigation behavior.
- The console remains compatible with mock payloads and future backend envelopes.

## Deferred

- Production authentication and authorization.
- Production Microsoft 365 integration.
- Real external source mutation.
- Real deletion execution.
- Persistent storage.
- Production parser, OCR, AI, and queue infrastructure.
- Certified compliance reporting.
- Final visual design system.
