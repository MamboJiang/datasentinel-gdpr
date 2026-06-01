# Frontend Console Contract

## Purpose

This document defines the functional contract for the internal lawdit product console. It tells frontend implementers what the console must support for P0 acceptance without prescribing visual design, component styling, layout composition, animation direction, or implementation architecture.

The console is the internal workspace simulation for a GDPR-relevant discovery workflow. It must make findings measurable, explainable, owner-routed, human-reviewed, audit-ready, and safe by default.

## Contract Sources

The console must stay aligned with `ACCEPTANCE.md`, `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, `contracts/mocks/`, `docs/PROJECT_CONTEXT.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, `docs/GOVERNANCE_CONFIG.md`, `docs/EVALUATION.md`, `docs/SECURITY_NOTES.md`, and the design notes under `docs/design/` for scan start, inventory/extraction, deterministic signal detection, context risk, owner routing, finding assembly, review support, human review, audit recording, incremental delta scan, account-menu utility actions, local language preference, sidebar resize/collapse, file review, and Workspace administration.

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
| `/workspace/admin` | Workspace administrator overview for compact member/group summaries, invitations, permission boundaries, and Workspace charts. |
| `/workspace/admin/groups` | Workspace group controls with group creation, permission editing, rename, and guarded deletion. |
| `/workspace/admin/members` | Workspace member directory with search, grouping, filtering, and sorting. |
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

The internal shell must provide current page title, a top-right session notification center with a non-destructive latest-message preview, top-left workspace context, bottom-left account controls, sidebar collapse/expand, desktop sidebar resize by pointer or keyboard separator, active-route indication, route navigation, keyboard-accessible menus, focus-safe close behavior, and responsive readability. The unauthenticated sign-in gate must use a minimal centered layout with lawdit branding and only branded Google/GitHub provider buttons. The top-left Workspace menu must be backed by Workspace data, show current membership groups when available, switch current Workspace when a member selects another Workspace, show legacy pending invitations when available, show a no-Workspace state for accounts that have not joined a Workspace, and open a Workspace creation dialog where a signed-in account can enter settings before creating a Workspace whose creator becomes `workspace_owner` and `workspace_admin`. Sidebar resize must collapse when dragged below the configured threshold and cap expansion at the configured maximum width. Sidebar destinations outside the current Workspace permission boundary must be hidden, and expandable sidebar groups must show a right-side chevron. Account menu controls must either navigate to a concrete local utility route or perform a clearly local UI action. Theme switching and language preference may use local browser state. Dark theme rendering must keep the Workspace switcher, Workspace creation dialog, sidebar navigation and subnavigation, Workspace Admin controls, and account-menu language selector on theme-aware surfaces with readable text and borders. Language preference uses static frontend dictionaries for user-facing UI copy; developer-facing docs, engineering notes, and code comments remain English-only. Feedback must remain local-only in P0. Log out, plan, and status controls must expose prototype boundaries instead of production authentication, billing, tenant, support, monitoring, or translation-service behavior. The shell must not mix public homepage navigation into the internal workspace shell or hide account, workspace, or permission context.

## Shared Data Contract

Every console surface that consumes API or mock data must handle the standard envelope: `data`, `meta`, and optional `pagination`. It must render `meta.contractVersion`, `meta.generatedAt`, `meta.traceId`, `meta.partial`, `meta.warnings`, and `application/problem+json` errors in an appropriate user-facing or diagnostic way. Scan start and review submission must preserve idempotency behavior when the backend or mock workflow provides it. When the project server is connected, the shared frontend read model must refresh Workspace-scoped read endpoints in the background so open Dashboard, Sources, Workspace Admin, Members, Groups, Findings, Audit, Evaluation, and Governance views reflect scan, review, source, member, and group changes without a manual browser refresh. Running scans may refresh more frequently than idle state. Background refresh must remain silent except for verified state transitions such as a same-scan `running -> completed` completion event.

## Surface Requirements

| Surface | Must cover | Safety and behavior requirements |
| --- | --- | --- |
| Dashboard | Default organizer source readiness; full-scan action for controlled `mock_ready` source; baseline-aware delta action; latest scan status/type; progress; scanned files; flagged files; scanned volume; duration; throughput; review backlog; high-risk count; retention-review or overdue count; human-review-required count; owner routing; pipeline stages; inventory/extraction; signal detection; context/risk; finding assembly; review support; audit recording; delta baseline and changed-file counts; aggregate management indicators; active policy version; evaluation and resource intensity. | Full and delta scans must use explicit `sourceId`; delta scans require a completed selected-source baseline; not-ready sources cannot create scans or audit events; duplicate starts cannot create conflicting records; running latest-scan state must show active loading and update from refreshed server state; aggregate metrics must show owner completion, risk queue, audit evidence, metric basis, and cost when available; raw content, legal conclusions, paid model usage, and deletion instructions must not appear. |
| Workspace admin | Current Workspace, configurable profile fields, current membership, compact member summary, compact group summary cards, compact invitation rows with pending-link copy controls, invitation link generation, Workspace creation, Owner transfer by active-member email, exact-name Workspace deletion, permission boundary, allowed/denied Workspace actions, and charts for membership distribution, invitation status, review load, scan/risk/audit metrics. | A signed-in account can create a Workspace and becomes its owner/admin. Switching Workspaces must reload Workspace-scoped operational state rather than copying data between Workspaces. Only Workspace admins may generate invite links or manage member/group data, and invite links must not grant `workspace_owner`. Invite-link acceptance must use concise copy and show the target Workspace name, introduction, owner, member count, and invited group when that context is available. Admins with `manage_workspace_settings` may change the Workspace name and introduction near the bottom of `/workspace/admin`; this must not imply billing, tenant, plan, legal, or compliance status. The top-left Workspace menu must keep membership groups in the compact right-side pill rather than in the Workspace name/description text block. Owners may transfer owner authority only after typing an exact email for another active Workspace member; the transfer control stays disabled until a match exists and requires a second confirmation before submission. Owners may delete the local Workspace only after exact-name confirmation and a second confirmation, and the Danger Zone remains the final page section. The admin overview and child pages must use concise operational labels instead of explanatory helper paragraphs or collapsed group-description text, while preserving Workspace description data, denied-action reasons, and deletion safety boundaries. The Members and Group controls panels must link to their dedicated admin subpages. Non-admins must see denied admin actions instead of silent hidden privilege and must not see sidebar destinations that require denied actions. New accounts without Workspace membership must see invitation-required state with create and invite-link acceptance options. Charts must not require a third-party dependency and must not imply legal certification. Workspace deletion must not delete external source files. |
| Workspace group controls | Workspace group list, group member counts, group permission counts, available permission catalog, new-group form, per-group rename and permission editor, and guarded group deletion. | Admins can create, rename, re-permission, and delete non-admin/non-owner groups from `/workspace/admin/groups`. Group controls must be collapsed by default, with the new-group form behind a single button and existing group editing behind a per-card edit icon. Protected owner/admin groups must preserve their required permissions and deletion guards. |
| Workspace members | Member name, email/account, groups, status, joined date, last activity, search controls, group filter, status filter, sort selector, grouping selector, member group editor, and remove-member control. | The directory must support all-member browsing, group/status filtering, grouping by group or status, sorting by name/group/status/joined/activity, guarded group reassignment, and guarded member removal. Member-management controls appear only when `manage_workspace_members` is allowed, cannot remove the current actor's own active membership, and must not expose provider tokens or hidden directory data. |
| Sources | Source ID/reference, name, type, status, root label, direct Source owner, fallback owner when present, reference URL, sample families, adapter readiness, source-specific scan action, connection test when available, source-owner edit action for admins, source-registration deletion, and delta scan start when a baseline can be represented. | Source-row scan must target the selected `sourceId`; the first source must not be hard-coded; Source setup and edit controls must use active Workspace members for owner assignment; Google Drive scan controls require a current in-memory Picker token or connected account-level Drive binding, and the row may show connected while either is available even though the persisted source record still stores no access token; missing, unreadable, expired-token, refresh-failed, or not-ready sources cannot create or preserve stale findings; source-registration deletion must clear derived lawdit workflow state for that source but must not claim or trigger source-file deletion. |
| Scan pipeline | `source_ready`, optional `comparing_delta_baseline`, `inventorying_files`, `extracting_content`, `detecting_signals`, `judging_context_risk`, `assigning_owner`, `assembling_findings`, `preparing_review_support`, `recording_audit_events`, and `completed` when present. | Stages must support pending, running, completed, warning, failed, unavailable, counts, warnings, and unknown-stage fallback. Ordering must not imply delta comparison before source readiness or context/risk, owner routing, review support, or audit before upstream evidence stages. |
| Inventory and extraction | Source snapshot ID, inventory fingerprint, candidate files, fingerprinted files, skipped files, total bytes, permission snapshots, sample-family distribution, extraction fingerprint, processed files, successful files, warning files, unsupported files, OCR-deferred files, redacted evidence candidates, extraction methods, recognition difficulty, format counts, and `rawContentExposed = false`. | Unsupported and OCR-deferred files are recoverable warnings, not hidden failures or blockers. Image OCR, video transcript, and bounded video frame OCR inputs must not expose raw media, frames, audio, or raw OCR/transcript text. No public extraction endpoint is required, and deterministic extraction must not imply AI usage. |
| Deterministic signal detection | Detector rules version/hash, policy-pack evidence requirements, evaluated evidence candidates, detected/redacted signal counts, findings-with-signals count, signal-type counts, warnings, and `rawContentExposed = false`. | Runs after extraction and before context/risk. It must expose redacted evidence only, not raw extracted text, file bodies, page images, detector secrets, legal conclusions, or deletion execution. |
| Findings list | Finding ID, scan ID, file name, safe source path/reference, risk level, score, context category, personal data types, retention status, recommended action, status, owner, assignment type, policy context, available actions, denied actions, pagination, and filters for scan, owner, risk, and status when available. | Empty, loading, partial, error, unknown risk/status, and missing optional owner fields must render. Raw sensitive values, external source URLs, and absolute host paths must not appear. |
| Finding detail | File context, risk, context category, personal data types, retention status, recommendation, status, policy context, owner assignment, file metadata, redacted signals, detector, confidence, location/fallback, risk explanation, available actions, denied actions, audit timeline, and top-bar hierarchy `Findings / Finding Detail`. | It must load the requested `/findings/{findingId}` detail rather than relying only on the first list row or summary data. It must open file review from header or evidence only when current review-support data grants finding review authority or the current workspace permission boundary grants `review_findings`; view-only actors must see disabled evidence navigation controls and the boundary reason. It must open review only after support/boundary context, let the non-current `Findings` title level navigate back to the list with a hover underline, tolerate empty audit timelines and unknown signals, hide unsafe source references behind a safe source label, and avoid legal conclusions. |
| File review editor | Open from finding detail, select first evidence by default, open from a specific evidence card, switch anchors, focus or highlight redacted preview regions, show redacted source-context windows, show fallback location, and close without changing state. | Only current finding reviewers or workspace actors with `review_findings` authority can open it. Only redacted snippets, masked values, redacted context windows, location labels, selector summaries, visual focus boxes, and safe metadata may appear. The editor must prefer contract `signal.evidenceAnchor` data, including PDF page, page-local offsets, CSV/Markdown/XLSX/ODS table cells, ZIP member ordinals, DOCX/PPTX/ODT/ODP/EML/HTML/XML/JSON/JSONL/NDJSON structure paths, estimated PDF page-region summaries, OCR image-region summaries, source-preview context windows, and normalized source-region focus when geometry is available, and fall back to legacy page/snippet data when anchors are absent. PDF, ZIP, DOCX, XLSX, ODT, ODS, ODP, EML, CSV, TXT, XML, JSONL/NDJSON, RTF, Markdown, image OCR, and unknown formats must have locator or fallback behavior. External source URLs and absolute source paths must not appear. |
| Review support | Finding ID, actor ID, policy-pack version, plain-language summary, available decisions, reason requirements, checklist, transfer options, escalation options, permission boundary, allowed actions, denied actions, and visible scopes. | Support must be finding-specific when data allows it. Decisions include `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate`. For Workspace findings, transfer options must come from active Workspace members returned by current review support and must not fall back to static demo delegation rows. |
| Review decision | Available decision validation, actor, non-empty reason, checklist acknowledgement when required, explicit deletion-candidate confirmation, retention review date for keep-with-reason when required, supported transfer target from active Workspace members, and supported queue for escalation. | Accepted decisions create one review record and one audit event, update visible state and metrics when available, and preserve policy/permission context. A retained decision must make the finding list and detail show retained retention state rather than unresolved needs-review state. Rejected decisions leave finding, audit, metrics, and source state unchanged. `delete_candidate` never mutates source files. |
| Audit | Event ID, type, actor, timestamp, scan/finding IDs, object details when available, previous/resulting state, outcome, reason, policy version, permission context, evidence reference count, summary, filtering, pagination, and consistency between global audit and finding timeline. | Human-entered text must be sanitized before display. Audit must not contain raw sensitive content. |
| Evaluation | Evaluation run, scan ID, dataset hash, scanner version, detector rules hash, signal-detection rules hash, context-risk hash, owner-assignment hash, finding-assembly hash, review-support hash, human-review hash, audit rules fingerprint, admin-metrics hash, config hash, finding fingerprint, precision, recall, F1, reproducibility, throughput, peak memory, CPU seconds, model calls, and estimated cost when available. | P0 must show zero model calls and zero estimated paid-service cost when provided. Mock values must not be represented as production-certified quality. Partial evaluation must show warnings. |
| Governance | Config ID, active policy pack, version, status, jurisdiction tags, effective dates, retention rules, risk guidance, evidence requirements, escalation paths, review decisions, organization model, owner-resolution strategy, org units, Master of Data fallback, delegation rules, source adapters, readiness, change controls, `realDeletionAllowed = false`, and change previews. | Governance actions must show denied reasons when unavailable. Historical policy context must remain visible in audit/finding views. Legal rules must not appear as hard-coded scanner logic. |
| Permission boundary | Actor ID, roles, allowed actions, denied actions, denial reasons, and visible scopes. | Boundaries must be shown before action, refreshed when actor context changes, and enforced on denied submissions. Denied actions should not be silently hidden when reasons exist. |

## Incremental Delta Scan Contract

When the contract provides delta data, the console must show baseline identity, changed/new/modified/unchanged/missing counts, processed changed files, carried-forward files or findings, reopened findings, and warnings. Missing files must be rendered as source inventory changes, not deletion. Delta state must preserve `rawContentExposed = false`, `legalConclusionProvided = false`, `missingFilesTreatedAsDeleted = false`, and `deletionExecuted = false` when those fields are available.

## Notifications and Status

The console should surface scan started, scan completed, scan rejected, partial data available, recoverable warning, review recorded, review rejected, audit event created, governance preview ready, and backend/mock unavailable states in the top-right session notification center, not bottom toast overlays. Scan-completed notifications must be emitted only after the frontend observes the same scan transition from `running` to `completed`; a fixed timeout or still-running scan state must not create a completed notification. New notifications should also appear in a small top-right latest-message preview that auto-dismisses after a few seconds without opening, closing, clearing, dismissing, or reordering the session notification center. Notifications must be timestamped, newest-first, dismissible, must not include raw sensitive content, and must not replace audit records.

## Error and Partial-State Contract

Every major surface must support loading, empty, partial data, recoverable warning, permission denied, validation error, not found, conflict or duplicate command, backend unavailable, and mock-backed fallback states. Problem details should show a concise user-facing message and preserve `traceId` for troubleshooting.

## Accessibility and Responsive Contract

The console must support keyboard navigation for routes, menus, dialogs, review actions, and file review; focus management for dialogs and overlays; visible focus states; screen-reader-readable labels for commands and statuses; reduced-motion compatibility; readable text at supported viewport sizes; and controls whose labels do not overflow.

The console must remain usable on desktop and mobile. Navigation, review actions, evidence cards, file review fallback, metrics, long file names, paths, policy versions, and reasons must remain reachable and readable without overlap.

## Acceptance Checklist

The console satisfies this contract when:

- Each implemented route consumes only fields documented in `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, `contracts/mocks/`, or tolerated optional fields.
- Dashboard, sources, findings, finding detail, file review, review, audit, evaluation, governance, permissions, and shared state surfaces are available or explicitly deferred for the current milestone.
- Workspace admin, Workspace menu, Workspace creation dialog, invitation-required state, and invitation acceptance are available for the current milestone.
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
