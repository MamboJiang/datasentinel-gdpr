# Design Specification

## Design Goal

The future product experience should make GDPR data cleanup feel like an accountable review workflow, not an automatic deletion tool.

## Conceptual Workflow State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Source selected | Full scan requested | Source is readable | Scanning | Record scan start |
| Scanning | File analyzed | File can be parsed | Finding classified | Store finding evidence |
| Scanning | File cannot be parsed | Error is recoverable | Needs review | Record extraction issue |
| Finding classified | Owner resolved | Owner confidence is sufficient | Assigned | Notify or queue owner |
| Finding classified | Owner unresolved | No reliable owner | Escalated | Queue for privacy team |
| Assigned | Reviewer opens task | Evidence card and permission boundary exist | Review supported | Show allowed decisions, denied actions, checklist, transfer, and escalation options |
| Assigned | Reviewer marks delete candidate | Reviewer is authorized and reason is recorded | Delete candidate | Record decision and no-deletion boundary |
| Assigned | Reviewer decides retain | Reviewer gives reason and retention review date | Retained | Record exception and review date |
| Assigned | Reviewer escalates | Escalation target exists | Escalated | Record escalation |
| Delete candidate | Deletion execution requested | Deletion is supported in a future approved scope | Closed | Record deletion result |
| Delete candidate | Deletion execution requested | Deletion is not supported in P0 | Needs review | Record denied deletion boundary |
| Closed | Delta scan requested | Previous scan baseline exists | Scanning changes | Compare changed files only |

## Experience Principles

- Show evidence, not hidden model conclusions.
- Mask sensitive snippets by default.
- Keep every decision attributable to a human or system actor.
- Make deletion, retention, and escalation reasons visible in the audit trail.
- Separate risk explanation from legal conclusion.
- Show scan quality metrics as first-class product evidence.
- Render partial data gracefully when the API reports `meta.partial = true`.
- Give users a clear sense of their permission boundary before they act.
- Make reviewer guidance operational through checklists, available decisions, transfer options, and escalation options.
- Separate authentication from authorization: Google/GitHub sign-in identifies the browser user, while permission boundaries still decide available workflow actions.
- Let users point DataSentinel at real files without implying that raw source files are uploaded into long-term product storage.

## P0 Information Architecture

| Surface | Purpose |
| --- | --- |
| Public Project Homepage | Introduce DataSentinel, explain the workflow, and link into the internal dashboard without showing the app shell. |
| Sign-In Gate | Let users start Google or GitHub login when configured, and show setup status when providers are unavailable. |
| App Shell, Workspace, and Account Menus | Show a page-title-focused top bar with notifications, keep workspace context in the top-left sidebar control, keep authenticated account controls in the bottom-left sidebar menu, and support sidebar collapse. |
| Source Connector | Select or register an allowed source and start full or delta scans. |
| Admin Dashboard | Show decision-oriented scan coverage, review queue, high-risk queue, owner routing, latest scan status, and pipeline health without overloading one panel. |
| Findings Table | Show risk-ranked findings filtered by owner, scan, status, or risk level. |
| Evidence Card | Show redacted evidence, signals, context, owner, retention status, and audit timeline. |
| File Review Editor | Open a redacted file preview from Finding Detail and focus the sensitive evidence anchor for review. |
| Review Panel | Let a human record a decision with a reason. |
| Audit View | Show scan and review events. |
| Evaluation Tab | Show accuracy, reproducibility, speed, and resource intensity. |
| Governance Settings | Show active policy pack, organization model, source adapters, and change controls. |
| Permission Boundary | Show allowed actions, denied actions, visible scopes, and denial reasons. |
| AI Processing Boundary | Show whether optional OpenRouter review support is disabled, missing a key, configured, or budget-blocked without exposing secrets or raw content. |

## Reviewer-Friendly Requirements

- Show a plain-language summary before every decision.
- Show why an action is allowed or denied.
- Show required reason fields before submit.
- Provide transfer and escalation options when ownership is unclear.
- Keep legal conclusions out of UI copy; show policy guidance and human decision requirements.

## Backend Planning Reference

The post-source backend planning sequence is documented in `docs/design/backend-post-source-execution-plan.md`, with stage details in `docs/design/backend-post-source-stage-details.md`. Product surfaces should stay aligned with that sequence:

- Admin dashboard reflects scan orchestration, metrics aggregation, and evaluation readiness.
- Findings table and evidence card reflect evidence assembly, context classification, risk planning, owner routing, and audit history.
- Review panel reflects review support, permission boundary, reason requirements, and human review command handling.
- Audit view reflects workflow state changes and human decisions.
- Delta scan presentation reflects changed-file-only processing against a prior full-scan baseline.

The frontend should request the project server through `/api` when available. Prelaunch deployments should show an unavailable or signed-out state instead of silently rendering fixture data. Local mock fallback may remain for explicit development/testing mode only, and both paths must preserve the same envelope, state, and no-deletion boundaries.

## Prelaunch Account Interaction

The account interaction is documented in `docs/design/prelaunch-account-system.md`.

- The app reads `/api/auth/session` before rendering the internal console.
- If no valid session exists, the app renders a sign-in gate backed by `/api/auth/providers`.
- Google and GitHub buttons navigate to backend login routes; the frontend does not receive provider tokens.
- The account menu renders the safe session profile and exposes logout through `/api/auth/logout`.
- Permission-boundary surfaces remain visible after login because authentication is not production authorization.
- The signed-in empty state must avoid fake findings before a source has been configured and scanned.

## Full Scan Start Interaction

The full-scan start interaction connects Source Connector and Admin Dashboard surfaces:

- The Dashboard starts a full scan against the default organizer sample source when that source is scan-ready.
- The Sources table starts a full scan against the selected source only when that source is scan-ready.
- A source that is not scan-ready must present a disabled or rejected action rather than silently creating a scan.
- Running scan state must show progress, partial counts, scanned volume, and audit activity.
- Completed scan state must show final counts, duration, throughput, and deterministic evaluation readiness.
- The interaction must not expose raw source text, claim legal conclusions, trigger deletion, or depend on unapproved production external APIs.

## Prelaunch Source Input Interaction

The source-input interaction is documented in `docs/design/google-drive-source-integration.md`.

- The Source Connector offers direct HTTPS file links, Google Drive selected files/folders, and host-allowed local paths as explicit modes.
- Google Drive selection opens the official Picker UI when host public credentials are configured.
- Drive file/folder selections store metadata only; the browser keeps the short-lived access token in memory and sends it only when starting a scan.
- Direct HTTPS links are treated as one-file sources and must show connection or scan errors when the URL fails policy checks.
- The UI states that DataSentinel reads source content during scan execution and stores metadata, redacted evidence, findings, and audit events.
- Source setup and empty states must avoid fake prefilled source rows or seeded findings in prelaunch mode.
- The UI must avoid raw source content, provider tokens, client secrets, legal conclusions, deletion execution, and broad tenant-access claims.

## Source Inventory and Content Extraction Interaction

The inventory and extraction interaction extends the Dashboard latest-scan and pipeline panels after a full scan starts:

- Running scan state shows inventory and extraction stages as partial work with recoverable warnings in the pipeline summary.
- Inventory details show candidate files, fingerprinted files, sample-family distribution, skipped files, and source snapshot identity.
- Extraction details show processed files, successful files, unsupported or OCR-deferred files, redacted evidence candidates, and supported extraction methods.
- The UI explicitly shows that raw source content is not exposed.
- Completed scan state marks inventory and extraction as complete while preserving duration, throughput, and deterministic evaluation readiness.
- The UI must avoid presenting extraction warnings as legal conclusions or deletion instructions.

## OpenRouter AI Assistive Processing Interaction

The AI assistive interaction is an operational boundary, not a default scan requirement:

- Health and scan metadata may show the current provider, model, budget guard, OCR/grep/AI tier plan, and safety boundaries.
- Metadata, text extraction, OCR, grep-rule stages, and active policy-pack context must run before AI context support is considered.
- AI context support can only use redacted evidence anchored to deterministic findings and mapped to the Atlas stage-4 context/risk boundary.
- AI runtime metadata should expose the 12 Atlas stage mapping so users can see that owner routing, permission boundaries, audit, delta governance, admin metrics, and evaluation remain outside AI authority.
- If the AI key is missing, the budget is exhausted, or usage cannot be checked in fail-closed mode, the UI should show a neutral unavailable state and continue the deterministic workflow.
- The UI must not expose the OpenRouter API key, raw source text, unredacted personal data, legal advice, GDPR-compliance claims, owner decisions, permission decisions, audit facts invented by AI, or deletion instructions.

## Deterministic Signal Detection Interaction

The signal-detection interaction extends the Dashboard latest-scan and pipeline panels after content extraction:

- Running scan state shows deterministic signal detection as pending until extraction is ready.
- Completed scan state shows detector rules version/hash, evidence requirements, detected/redacted signal counts, findings-with-signals count, and signal-type counts.
- The pipeline summary shows `detecting_signals` after `extracting_content` and before `judging_context_risk`.
- Finding details continue to show redacted detector evidence with detector, confidence, snippet, and location when available.
- The UI must avoid raw source content, unredacted personal data, detector secrets, legal conclusions, deletion instructions, or claims of GDPR compliance.

## Context and Risk Judgment Interaction

The context/risk interaction extends the Dashboard review focus and pipeline summary after signal detection:

- Running scan state shows context/risk judgment as pending until evidence candidates and signal detection are ready.
- Completed scan state shows risk-assessed findings, high-risk findings, retention-review files, human-review-required findings, and policy-pack version.
- The pipeline summary shows `judging_context_risk` after `detecting_signals`.
- The UI shows that no legal conclusion is provided by the automated stage.
- The UI must avoid raw source content, unredacted personal data, deletion instructions, or claims of GDPR compliance.

## Owner Routing and Assignment Interaction

The owner-routing interaction extends the Dashboard review focus and pipeline summary after context/risk judgment:

- Running scan state shows owner assignment as pending until context/risk judgment is complete.
- Completed scan state shows assigned findings, Master of Data fallback assignments, escalation assignments, and unowned findings.
- The pipeline summary shows `assigning_owner` after `judging_context_risk`.
- The UI shows routing strategy and organization-model version as operational accountability context.
- The UI must avoid legal conclusions, raw source content, unredacted personal data, hidden permission decisions, production directory assumptions, and deletion instructions.

## Finding Assembly and Evidence Card Interaction

The finding-assembly interaction connects completed owner routing to the findings table and evidence-card detail view:

- Running scan state shows finding assembly as pending until owner assignment and redacted signals are complete.
- Completed scan state shows assembled findings, evidence cards, redacted evidence signals, and missing-card count.
- The pipeline summary shows `assembling_findings` after `assigning_owner`.
- Findings table rows show evidence signal count when the contract provides it.
- Evidence cards show redacted signals, policy context, owner assignment, retention status, action boundary, and audit timeline.
- The UI shows allowed and denied actions before review submission when the contract provides them.
- The UI must avoid legal conclusions, raw source content, unredacted personal data, hidden permission decisions, production parser assumptions, and deletion instructions.

## Review Support and Permission Boundary Interaction

The review-support interaction connects assembled evidence cards to human-review readiness:

- Running scan state shows review support as pending until finding assembly and permission-boundary calculation are ready.
- Completed scan state shows supported findings, available decision count, required reason count, checklist count, transfer count, escalation count, denied action count, and policy-pack version.
- The pipeline summary shows `preparing_review_support` after `assembling_findings`.
- The Review Dialog uses finding-specific support instead of a disconnected static fixture.
- The dialog shows delete candidate, keep with reason, false positive correction, reassign, and escalate decisions when allowed.
- Missing reasons, denied decisions, missing transfer targets, and missing escalation queues are rejected before state changes.
- The UI must avoid legal conclusions, raw source content, unredacted personal data, hidden permission decisions, production authorization assumptions, and deletion execution.

## Human Review Decision Handling Interaction

The human-review decision interaction connects review support to outcome state, audit, and metrics:

- The Review Dialog submits only decisions exposed by current finding-specific review support.
- Required checklist items must be acknowledged before submit.
- The retain decision shows and requires a retention review date.
- Transfer and escalation decisions show only supported owner or queue targets.
- Accepted decisions update the visible finding status, audit timeline, global audit list, review backlog, and outcome metrics.
- Repeated submissions with the same command key do not duplicate audit events or metrics.
- Denied, incomplete, or stale decisions show a neutral rejection and leave visible state unchanged.
- Delete candidate remains a review status only; the UI must not imply source-file deletion or deletion execution.
- The UI must avoid legal conclusions, raw source content, unredacted personal data, hidden permission decisions, production authorization assumptions, and deletion execution.

## Audit Event Recording Interaction

The audit-recording interaction connects visible workflow changes to an accountable trail:

- The pipeline summary shows `recording_audit_events` after `preparing_review_support`.
- The Audit page shows structured action, outcome, actor type, object type, object ID, timestamp, reason when available, and evidence reference count.
- Finding detail audit timelines and the global audit list use the same audit-event shape.
- Accepted review decisions update the finding timeline, global audit list, audit-recording summary, audit metrics, and evaluation traceability together.
- Human-entered audit reason text is sanitized before public display.
- The UI must avoid legal conclusions, raw source content, unredacted personal data, hidden permission decisions, production log-management assumptions, and deletion execution.

## Incremental Delta Scan Interaction

The incremental delta-scan interaction connects a completed baseline to changed-file-only follow-up scanning:

- Dashboard and Sources expose delta scan actions only when the selected source is scan-ready and a completed baseline can be represented.
- A rejected delta start shows a neutral unavailable state and does not create scan, audit, finding, metric, or evaluation changes.
- Running delta state shows `comparing_delta_baseline` before changed-file inventory and extraction.
- Delta summary shows baseline scan ID, changed, new, modified, unchanged, and missing file counts when available.
- Completed delta state shows changed-file findings with the delta scan ID while unchanged baseline files are carried forward.
- Missing files are presented as source inventory changes, not DataSentinel deletion or proof of erasure.
- The UI must avoid legal conclusions, raw source content, unredacted personal data, hidden permission decisions, production connector assumptions, and deletion execution.

## Admin Metrics Aggregation Interaction

The admin-metrics interaction turns prior workflow outputs into management indicators:

- Running scans show aggregate metrics as partial and identify the upstream stage basis used for the numbers.
- Completed scans show scan coverage, risk queue, owner backlog, review throughput, review outcomes, audit evidence, evaluation linkage, and resource cost as one management view.
- Completed delta scans show changed, processed, carried-forward, and missing-file counts while preserving the no-deletion boundary.
- Accepted review decisions update owner backlog, outcomes, audit counts, and throughput indicators without duplicating idempotent submissions.
- The Dashboard shows owner task completion, risk queue, audit evidence, metric basis, and estimated service cost without exposing raw content or implying legal conclusions.
- The UI must avoid raw source content, unredacted personal data, hidden permission decisions, production analytics assumptions, legal advice, and deletion execution.

## Evaluation Metrics Generation Interaction

The evaluation interaction turns prior workflow outputs into measurable quality evidence:

- The pipeline summary shows `generating_evaluation_metrics` after `recording_audit_events`.
- Completed scan state shows precision, recall, F1, reproducibility, throughput, resource intensity, confusion-matrix counts, scenario-level metrics, review-throughput context, and risk-progress fields.
- Full-scan evaluation uses a controlled golden dataset definition and shows false-positive, false-negative, unsupported-file, and OCR-deferred-file context.
- Delta evaluation shows changed-file quality context while preserving baseline, carried-forward, missing-file, and no-deletion boundaries.
- Accepted review decisions refresh review-throughput and risk-progress evaluation context without changing scan-quality precision, recall, or F1.
- The Evaluation page shows the dataset, upstream stage basis, rule fingerprints, resource and cost boundaries, and safety boundaries.
- The UI must avoid raw source content, unredacted personal data, hidden permission decisions, production evaluation assumptions, legal advice, full-compliance claims, and deletion execution.

## File Review Editor Interaction

The file review editor adds source-context inspection to Finding Detail:

- The editor opens from the finding header or from a redacted evidence card.
- Opening from the finding header focuses the first available evidence anchor.
- Opening from an evidence card focuses that evidence anchor.
- The preview shows only redacted evidence snippets and location fallback labels until explicit file-rendering anchors are added to the contract.
- The editor must support unsupported or imprecise file formats by showing a redacted fallback location instead of blocking review.
- Closing the editor must not change scan state, finding state, source files, or review state.

## Public Homepage Interaction

The public homepage separates project introduction from the internal operations workspace:

- `/` shows the public project homepage.
- `/dashboard` shows the internal dashboard inside the app shell.
- The homepage visually explains discovery, redacted evidence, owner routing, human review, audit trails, governance, and evaluation.
- Homepage motion uses scroll-linked parallax only as progressive enhancement.
- Users with reduced-motion preferences must receive the same readable content without required animation.

## Deferred Design Decisions

- Visual design system.
- Interaction details.
- Framework-specific components.
- Production data persistence model beyond the local SQLite P0 state file.
