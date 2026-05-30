# Acceptance Criteria

## Repository Initialization

The initialization is complete when:

- The GitHub repository is public.
- The local repository has a clean `main` branch after the initial commit is pushed.
- The repository contains English-language planning documents for BRD, MRD, PRD, TRD, DesignSpec, TestCase, and acceptance criteria.
- The repository does not contain implementation code, runtime dependencies, secrets, generated build artifacts, or copied source data from the challenge PDF.
- The project README clearly states the project thesis, current scope, and non-goals.
- The listed teammates are invited as GitHub collaborators.

## Project Readiness

The project is ready for implementation only when:

- The team approves the initial requirements and acceptance criteria.
- The first implementation task has a narrow, testable scope.
- Any new workflow, external API integration, permission model, or deletion mechanism has a design note with state transitions, failure paths, rollback paths, and primitive acceptance criteria.

## Parallel Delivery Contract Readiness

Frontend-backend parallel development may start when:

- `docs/API_CONTRACT.md` defines the P0 endpoints, envelope, tolerance rules, error format, and state machines.
- `contracts/openapi.yaml` and `contracts/schemas/` define the machine-readable contract.
- `contracts/mocks/` contains payloads for sources, scan status, findings list, finding detail, audit events, admin metrics, and latest evaluation.
- `docs/DELIVERY_WORKFLOW.md` defines frontend, backend, contract, and QA responsibilities.
- `AGENTS.md` and `.github/copilot-instructions.md` tell teammate AI tools how to follow the contract.
- No frontend or backend implementation code is introduced before the first scoped implementation task.
- `docs/GOVERNANCE_CONFIG.md` defines policy packs, organization model, permission boundaries, review support, and enterprise change scenarios.
- `docs/GDPR_SAMPLE_REFERENCES.md` records how the organizer sample repository is used without vendoring PDFs.

## Frontend Surface Contract Readiness

Frontend surface work is ready for final implementation and QA planning when:

- `docs/FRONTEND_CONSOLE_CONTRACT.md` defines the internal console functional contract across app shell, dashboard, sources, scan pipeline, findings, finding detail, file review, review support, human review, audit, evaluation, governance, permissions, states, privacy boundaries, and responsive/accessibility obligations.
- `docs/WEBSITE_HOMEPAGE_CONTRACT.md` defines the public homepage content contract across product thesis, workflow highlights, sample source, evidence/redaction, owner routing, human review, audit, evaluation, governance, safety boundaries, calls to action, reduced motion, and responsive/accessibility obligations.
- Both frontend surface contracts avoid prescribing visual design, component implementation, final art direction, framework internals, or unapproved dependencies.
- Both frontend surface contracts remain compatible with `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, `contracts/mocks/`, `docs/DesignSpec.md`, and the current P0 acceptance criteria.
- Both frontend surface contracts keep repository and user-facing content English-only, keep deletion simulated, avoid legal-advice or full-compliance claims, and avoid production Microsoft Graph, OAuth, tenant, AI, parser, OCR, database, queue, or deletion commitments.

## Backend Post-Source Planning Readiness

Backend work after sample source connection is ready to break into scoped tasks when:

- `docs/design/backend-post-source-execution-plan.md` and `docs/design/backend-post-source-stage-details.md` define the planned stages from full scan through evaluation metrics.
- The planning documents cover scan orchestration, inventory and extraction, deterministic signal detection, context and risk planning, owner routing, finding assembly, review support, human review, audit logging, delta scan planning, admin metrics, and evaluation.
- The planning documents define state transitions, guard conditions, side effects, failure paths, partial-data behavior, and rollback path.
- The planning documents map the organizer sample families to evidence, context, owner-routing, and review planning assumptions without making legal conclusions.
- The planning documents stay compatible with `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, and existing mock fixtures without requiring a contract version bump.
- The planning documents keep raw sensitive text out of public responses and keep deletion simulated.
- `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, and `docs/TestCase.md` reference the post-source backend planning sequence.

## P0 Product Acceptance

The first implementation milestone is accepted when:

- The root route `/` shows a public project homepage that introduces DataSentinel and links to the internal dashboard route at `/dashboard`.
- The frontend app shell shows only the current page title plus notifications in the top bar, keeps workspace switching in the top-left sidebar control, exposes logged-in account controls from the bottom-left sidebar account menu, and lets users collapse or expand the sidebar.
- On desktop, the sidebar can be resized with a pointer or keyboard-accessible separator, collapses when dragged below the configured threshold, caps expansion at the configured maximum width, and keeps the content area aligned without overlap.
- Account menu actions open local utility routes or local UI states for account settings, theme, language preference, feedback, homepage, changelog, help, docs, platform status, prototype plan, and session boundary without adding production authentication, billing, support, monitoring, tenant, external translation, or external feedback integration.
- The account menu language preference lists EU language options, persists the selected code locally, keeps interface copy English-only in P0, and does not call a backend or translation service.
- A full scan can be started on a controlled sample source.
- Starting a full scan uses an explicit `sourceId`, is allowed only for the controlled `mock_ready` sample source in P0, and records scan-start and scan-completion audit events in the mock workflow.
- The Dashboard groups scanned files, flagged files, scanned volume, progress, scan time, review backlog, high-risk count, retention review count, and owner routing into clear scan, review, and pipeline summaries.
- A responsible user can list assigned findings.
- A finding detail view shows redacted evidence, signals, risk explanation, owner assignment, retention status, and audit timeline.
- A reviewer can open a redacted file review surface from a finding detail view and focus the relevant sensitive evidence location without exposing raw sensitive values.
- A human reviewer can record delete candidate, keep with reason, false positive, reassign, or escalate decisions.
- Every review decision creates an audit event with actor, timestamp, reason, and resulting status.
- A delta scan can run as a changed-file-only workflow against a completed full-scan baseline.
- Evaluation metrics show precision, recall, F1, reproducibility, throughput, and resource intensity.
- Deletion remains simulated.

## Full Scan Start Acceptance

The full-scan start stage is accepted when:

- The design note `docs/design/full-scan-start-workflow.md` defines scope, state transitions, failure paths, rollback path, and primitive acceptance criteria.
- Dashboard full-scan start targets the default organizer sample source by `sourceId`.
- Source-row full-scan start targets the selected source by `sourceId`.
- Not-ready sources cannot create a full-scan record or audit event.
- Running and completed scan states update visible admin metrics without exposing raw source content.
- Evaluation data remains deterministic and cost-free for P0, with no model calls required for this stage.
- Automated behavior tests cover the accepted and rejected start paths.

## Source Inventory and Content Extraction Acceptance

The source-inventory and content-extraction stage is accepted when:

- The design note `docs/design/source-inventory-content-extraction.md` defines scope, state transitions, failure paths, rollback path, research basis, and primitive acceptance criteria.
- Starting a full scan produces visible file-inventory and content-extraction summaries for the selected controlled source without adding a public extraction endpoint.
- Internal inventory records include file path, size, modified timestamp, sample family, readability status, and file fingerprint for each candidate file.
- Running scans mark partial data with recoverable warnings and do not expose raw extracted text, file bodies, page images, or unredacted personal data.
- Completed scans show candidate files, fingerprinted files, extracted files, redacted evidence candidates, warning counts, duration, throughput, and evaluation resource intensity.
- Unsupported or OCR-deferred files are counted as recoverable warnings instead of silently failing or blocking the scan.
- The implementation uses deterministic fixture-backed processing with zero model calls and zero estimated paid-service cost.
- Automated behavior tests cover running, completed, partial-warning, no-raw-content, unsupported-file warning, and not-ready-source paths.

## Deterministic Signal Detection Acceptance

The deterministic signal-detection stage is accepted when:

- The design note `docs/design/deterministic-signal-detection.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `detecting_signals` after `extracting_content` and before `judging_context_risk`.
- Running scans show signal detection as pending until extraction completes.
- Completed scans expose a `signalDetection` summary with detector rules version/hash, active evidence requirements, evaluated evidence candidates, detected signals, redacted signals, findings-with-signals, signal-type counts, warnings, and `rawContentExposed = false`.
- Finding details expose only redacted signal snippets with detector, confidence, and location when available; no raw extracted text, file bodies, page images, detector secrets, or unredacted personal data crosses public payloads.
- Admin metrics expose signal counts, and evaluation preserves a signal-detection rules hash plus deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, signal-detection, finding, audit, metric, or evaluation state changes.
- Automated behavior tests cover running, completed, redaction boundary, rules hash, metrics, evaluation traceability, and not-ready-source paths.

## Context and Risk Judgment Acceptance

The context-and-risk judgment stage is accepted when:

- The design note `docs/design/context-risk-judgment.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `judging_context_risk` after `detecting_signals` and before completion.
- Running scans show context/risk judgment as pending until extraction and signal detection complete.
- Completed scans expose a `contextRisk` summary with policy-pack version, risk-rule fingerprint, assessed evidence count, context and risk counts, retention-review count, human-review count, and `legalConclusionProvided = false`.
- The stage consumes redacted signal/evidence candidates, sample-family metadata, modified-time context, and active policy-pack guidance without exposing raw source content or unredacted personal data.
- The Dashboard shows context/risk status, policy version, high-risk count, retention-review count, and human-review count without presenting legal conclusions.
- Evaluation preserves a context-risk rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, or audit state changes.
- Automated behavior tests cover running, completed, policy-pack version, no-legal-conclusion, no-raw-content, cost boundary, and not-ready-source paths.

## Owner Routing and Assignment Acceptance

The owner-routing and assignment stage is accepted when:

- The design note `docs/design/owner-routing-assignment.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived continuity requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `assigning_owner` after `judging_context_risk` and before completion.
- Running scans show owner assignment as pending until context/risk judgment completes.
- Completed scans expose an `ownerAssignment` summary with policy-pack version, organization-model version, owner-resolution strategy, assignment-rule fingerprint, assigned count, direct-owner count, Master of Data fallback count, escalation count, and `unownedFindings = 0`.
- The stage consumes context/risk human-review counts, source Master of Data metadata, organization model, and active policy-pack escalation paths without exposing raw source content or unredacted personal data.
- The Dashboard shows owner-routing status, assigned findings, fallback assignments, escalation assignments, and unowned count without presenting legal conclusions.
- Owner routing creates an audit-visible event when review-required findings are routed.
- Evaluation preserves an owner-assignment rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, owner-assignment, or audit state changes.
- Automated behavior tests cover running, completed, fallback, escalation, no-unowned, audit, no-raw-content, cost boundary, and not-ready-source paths.

## Finding Assembly and Evidence Card Acceptance

The finding-assembly and evidence-card stage is accepted when:

- The design note `docs/design/finding-assembly-evidence-card.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `assembling_findings` after `assigning_owner` and before completion.
- Running scans show finding assembly as pending until owner assignment and redacted signals are complete.
- Completed scans expose a `findingAssembly` summary with policy-pack version, source snapshot, assembly fingerprint, assembled finding count, evidence-card count, redacted signal count, missing-card count, denied-action count, `rawContentExposed = false`, and `legalConclusionProvided = false`.
- Completed scan findings and evidence-card details are assembled from the completed scan ID and previous stage summaries instead of disconnected static rows.
- Each assembled evidence card shows redacted signals, policy context, owner assignment, retention status, action boundary, and audit timeline without exposing raw source content or unredacted personal data.
- Finding assembly creates an audit-visible event and evaluation preserves a finding-assembly rules hash.
- The stage keeps deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, finding, evidence-card, or audit state changes.
- Automated behavior tests cover running, completed, scan continuity, redaction, no-legal-conclusion, action-boundary, ownerless escalation, audit, evaluation hash, cost boundary, and not-ready-source paths.

## Review Support and Permission Boundary Acceptance

The review-support and permission-boundary stage is accepted when:

- The design note `docs/design/review-support-permission-boundary.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `preparing_review_support` after `assembling_findings`.
- Running scans show review support as pending until finding assembly and permission-boundary calculation can complete.
- Completed scans expose a `reviewSupport` summary with policy-pack version, organization-model version, support rules fingerprint, supported finding count, allowed action count, denied action count, available decision count, required reason count, checklist count, transfer count, escalation count, `rawContentExposed = false`, and `legalConclusionProvided = false`.
- Finding-specific review support is derived from assembled evidence cards, owner assignment, active policy pack, organization model, and actor permission boundary instead of disconnected static rows.
- A reviewer can see delete candidate, keep with reason, false positive correction, reassign, and escalate options when those actions are inside the permission boundary.
- Every available review decision requires a human reason before submission.
- Denied actors, missing reasons, missing transfer targets, and missing escalation targets are rejected without changing finding, audit, source, or metric state.
- Real deletion remains denied and visible as a permission-boundary reason.
- Evaluation preserves a review-support rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, review-support, permission-boundary, finding, evidence-card, or audit state changes.
- Automated behavior tests cover running, completed, finding-specific support, permission denial, reason validation, target validation, no-raw-content, no-legal-conclusion, evaluation hash, cost boundary, and not-ready-source paths.

## Human Review Decision Handling Acceptance

The human-review decision-handling stage is accepted when:

- The design note `docs/design/human-review-decision-handling.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A review decision is accepted only when current finding-specific review support exposes the decision inside the actor permission boundary.
- A reviewer can submit `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate` decisions with required human context.
- Every accepted decision creates exactly one review record and one audit event with actor, timestamp, decision, reason, resulting status, policy-pack version, permission-boundary fingerprint, and review-support rules fingerprint when available.
- `delete_candidate` changes finding review status only; no source file, connector, deletion service, or real deletion state is changed.
- `keep_with_reason` requires and records a retention review date.
- `reassign_owner` requires and records a supported transfer target.
- `escalate` requires and records a supported escalation queue.
- Denied decisions, denied actors, actor mismatch, missing reasons, missing checklist acknowledgements, missing retention review dates, missing transfer targets, missing escalation queues, and unknown findings are rejected without changing finding, audit, source, metric, or evaluation state.
- Duplicate review submissions with the same idempotency key do not create duplicate audit events or metric increments.
- Admin metrics can expose review decision totals, outcome counts, backlog movement, and review throughput inputs.
- Evaluation can preserve a human-review decision rules hash while keeping deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Automated behavior tests cover accepted decisions, audit creation, status/owner updates, retain-date validation, checklist validation, denial paths, idempotency, no-real-deletion, metrics, evaluation, and no-state-change failures.

## Audit Event Recording Acceptance

The audit-event recording stage is accepted when:

- The design note `docs/design/audit-event-recording.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `recording_audit_events` after `preparing_review_support`.
- Audit events for scan start, scan completion, owner assignment, finding assembly, finding assembled, finding assigned, and accepted review decisions share a structured event shape with actor, action, object, timestamp, state transition, outcome, and evidence references.
- Completed scan state exposes an `auditRecording` summary with policy-pack version, audit rules fingerprint, recorded event count, linked scan count, linked finding count, review decision count, human/system counts, `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false`.
- Accepted review decisions update the finding audit timeline, global audit list, audit summary, audit metrics, and evaluation traceability together.
- Denied, incomplete, stale, unknown, or duplicate review commands do not create duplicate audit events or metric increments.
- Human-entered audit text is sanitized for obvious emails, IBAN-like values, long numbers, and control characters before it appears in public audit payloads.
- The implementation keeps deterministic reproducibility, zero model calls, zero estimated paid-service cost, and no production storage, connector, authorization, SIEM, or deletion integration.
- Automated behavior tests cover lifecycle event recording, finding timeline inclusion, structured audit metadata, text sanitization, audit metrics, evaluation hash, no-raw-content boundary, and no-real-deletion boundary.

## Incremental Delta Scan Acceptance

The incremental delta-scan stage is accepted when:

- The design note `docs/design/incremental-delta-scan-workflow.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A delta scan can start only for a selected scan-ready source with a completed baseline; missing, running, not-ready, or mismatched baselines reject without scan, audit, finding, metric, or evaluation state changes.
- Running delta scans expose `comparing_delta_baseline`, baseline identity, changed/new/modified/unchanged/missing counts, partial warnings, and `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false`.
- Completed delta scans process only changed files, carry unchanged baseline files forward, and represent missing files as source inventory changes rather than DataSentinel deletion.
- Completed delta findings use the delta scan ID and pass through context/risk, owner routing, finding assembly, review support, audit recording, metrics, and evaluation instead of using disconnected static rows.
- Dashboard and Sources expose delta readiness from the selected source and show baseline/change counts when available.
- Evaluation preserves a delta rules hash, deterministic reproducibility, throughput, zero model calls, and zero estimated paid-service cost.
- Automated behavior tests cover accepted delta start, rejected baseline paths, completed changed-file processing, carried-forward counts, no-real-deletion boundary, audit, metrics, evaluation, and full-scan continuity.

## Admin Metrics Aggregation Acceptance

The aggregate admin-metrics stage is accepted when:

- The design note `docs/design/admin-metrics-aggregation.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- Running scans expose partial aggregate metrics that identify upstream stage status across inventory, extraction, context/risk, owner assignment, finding assembly, review support, audit recording, and delta when present.
- Completed scans expose aggregate management metrics for scan coverage, deterministic signal counts, risk queue, owner backlog, review throughput, review outcomes, audit evidence, evaluation linkage, and resource cost from prior stage summaries instead of disconnected constants.
- Completed delta scans preserve changed-file, carried-forward, missing-file, no-raw-content, no-legal-conclusion, and no-deletion boundaries in the aggregate metrics.
- Accepted review decisions update owner backlog, outcome counters, audit counts, throughput inputs, and evaluation-linked aggregation exactly once.
- Rejected scan or review attempts leave metric, audit, source, finding, and evaluation state unchanged.
- Aggregated metrics keep `rawContentExposed = false`, `legalConclusionProvided = false`, `deletionExecuted = false`, `modelCalls = 0`, and `estimatedCostUsd = 0` in P0.
- Evaluation preserves an admin-metrics rules hash for deterministic reproducibility.
- Dashboard shows management indicators for owner completion, risk queue, audit evidence, metric basis, and cost without exposing raw source content or legal conclusions.
- Automated behavior tests cover running aggregation, completed aggregation, delta aggregation, accepted review metric updates, rejected path identity, safety boundaries, and cost boundaries.

## Evaluation Metrics Generation Acceptance

The evaluation-metrics generation stage is accepted when:

- The design note `docs/design/evaluation-metrics-generation.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- Completed full scans generate precision, recall, F1, reproducibility, throughput, resource intensity, confusion-matrix counts, scenario-level metrics, review-throughput context, and risk-progress fields from prior workflow summaries and a controlled golden dataset definition.
- Completed delta scans generate changed-file evaluation while preserving baseline, carried-forward, missing-file, no-raw-content, no-legal-conclusion, no-deletion, zero-model-call, and zero-cost boundaries.
- Evaluation exposes an evaluation-rules fingerprint plus dataset, detector/signal-detection, config, policy-pack, context/risk, owner-assignment, finding-assembly, review-support, audit-recording, admin-metrics, delta, and finding fingerprints for deterministic reproduction.
- Accepted human-review decisions refresh review-throughput and risk-progress fields exactly once without changing scan-quality precision, recall, or F1.
- Rejected scan or review commands leave evaluation, metric, audit, source, and finding state unchanged.
- The Evaluation page renders scan quality, confusion matrix, scenario metrics, resource intensity, reproducibility, and safety boundaries without raw source content or legal conclusions.
- Automated behavior tests cover full-scan generation, delta generation, review refresh, rejected-path identity, metric formula bounds, safety boundaries, and cost boundaries.

## Adaptive Governance Acceptance

The design points are accepted when:

- Legal or policy details can be represented as a versioned policy pack instead of hard-coded scanner logic.
- A reviewer can see plain-language support, required checklist items, available decisions, transfer options, escalation options, and required reason fields.
- A user can see allowed actions, denied actions, denial reasons, and visible scopes before attempting an action.
- Ownership transfer, personnel change, organization model change, policy version change, and regulatory update scenarios are represented in docs and contract mocks.
- Audit and evaluation payloads can preserve the policy-pack version used for a finding or decision.
- The organizer sample repository is represented as a default demo source with sample families.

## Remote Preview Deployment Acceptance

The remote preview deployment is accepted when:

- The design note `docs/design/remote-preview-deployment.md` defines problem, options, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `docs/DEPLOYMENT.md` records the `agent-us` static preview layout, Caddy route, validation commands, and rollback steps.
- `npm run test` and `npm run build` pass before deployment.
- The remote host serves the frontend through Caddy on port 80 from `/srv/datasentinel/frontend/current`.
- Direct requests for `https://founder-force.uk/` and `https://founder-force.uk/dashboard` return DataSentinel frontend HTML after DNS points to `agent-us`.
- The preview remains mock-backed and adds no backend API, production Microsoft Graph, OAuth, tenant, AI, database, queue, or deletion service.
- The previous Caddyfile is saved before modification, and the release symlink allows asset rollback.
