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

## P0 Information Architecture

| Surface | Purpose |
| --- | --- |
| Public Project Homepage | Introduce DataSentinel, explain the workflow, and link into the internal dashboard without showing the app shell. |
| App Shell, Workspace, and Account Menus | Show a page-title-focused top bar with notifications, keep workspace context in the top-left sidebar control, keep logged-in account controls in the bottom-left sidebar menu, and support sidebar collapse. |
| Source Connector | Select a controlled demo source and start full or delta scans. |
| Admin Dashboard | Show decision-oriented scan coverage, review queue, high-risk queue, owner routing, latest scan status, and pipeline health without overloading one panel. |
| Findings Table | Show risk-ranked findings filtered by owner, scan, status, or risk level. |
| Evidence Card | Show redacted evidence, signals, context, owner, retention status, and audit timeline. |
| File Review Editor | Open a redacted file preview from Finding Detail and focus the sensitive evidence anchor for review. |
| Review Panel | Let a human record a decision with a reason. |
| Audit View | Show scan and review events. |
| Evaluation Tab | Show accuracy, reproducibility, speed, and resource intensity. |
| Governance Settings | Show active policy pack, organization model, source adapters, and change controls. |
| Permission Boundary | Show allowed actions, denied actions, visible scopes, and denial reasons. |

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

## Full Scan Start Interaction

The full-scan start interaction connects Source Connector and Admin Dashboard surfaces:

- The Dashboard starts a full scan against the default organizer sample source when that source is scan-ready.
- The Sources table starts a full scan against the selected source only when that source is scan-ready.
- A source that is not scan-ready must present a disabled or rejected action rather than silently creating a scan.
- Running scan state must show progress, partial counts, scanned volume, and audit activity.
- Completed scan state must show final counts, duration, throughput, and deterministic evaluation readiness.
- The interaction must not expose raw source text, claim legal conclusions, trigger deletion, or depend on production external APIs.

## Source Inventory and Content Extraction Interaction

The inventory and extraction interaction extends the Dashboard latest-scan and pipeline panels after a full scan starts:

- Running scan state shows inventory and extraction stages as partial work with recoverable warnings in the pipeline summary.
- Inventory details show candidate files, fingerprinted files, sample-family distribution, skipped files, and source snapshot identity.
- Extraction details show processed files, successful files, unsupported or OCR-deferred files, redacted evidence candidates, and supported extraction methods.
- The UI explicitly shows that raw source content is not exposed.
- Completed scan state marks inventory and extraction as complete while preserving duration, throughput, and deterministic evaluation readiness.
- The UI must avoid presenting extraction warnings as legal conclusions or deletion instructions.

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
- Data persistence model.
