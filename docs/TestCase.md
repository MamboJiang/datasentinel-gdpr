# Test Cases

## Current Initialization Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| INIT-001 | Review repository language | All tracked project files are written in English. |
| INIT-002 | Review repository scope | No implementation code or runtime dependency files are present. |
| INIT-003 | Review required documents | README, BRD, MRD, PRD, TRD, DesignSpec, TestCase, and ACCEPTANCE exist. |
| INIT-004 | Review GitHub visibility | The remote repository is public. |
| INIT-005 | Review collaborators | Requested teammates are invited or already present as collaborators. |

## Contract Readiness Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| CONTRACT-001 | Parse contract YAML files | `contracts/openapi.yaml` and files in `contracts/schemas/` parse as YAML. |
| CONTRACT-002 | Parse mock payloads | Every file in `contracts/mocks/` parses as JSON. |
| CONTRACT-003 | Compare contract docs and mocks | Mock payloads use the envelope, field names, and state values documented in `docs/API_CONTRACT.md`. |
| CONTRACT-004 | Review tolerant compatibility rules | Unknown fields, optional fields, empty arrays, partial data, and unknown enum-like values have documented behavior. |
| CONTRACT-005 | Review error contract | Errors are documented as `application/problem+json` with trace IDs. |
| CONTRACT-006 | Review AI instructions | `AGENTS.md` and `.github/copilot-instructions.md` tell AI tools to follow the contract and avoid unapproved implementation. |
| CONTRACT-007 | Review governance contract | Governance config, active policy pack, permissions, and review support endpoints are documented and mocked. |
| CONTRACT-008 | Review organizer sample source | The organizer sample repository is represented as a default demo source without vendoring PDFs. |

## Backend Planning Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| BEPLAN-001 | Review post-source execution plan | `docs/design/backend-post-source-execution-plan.md` and `docs/design/backend-post-source-stage-details.md` define the backend steps after sample source connection. |
| BEPLAN-002 | Review step boundaries | The planning documents separate scan orchestration, extraction, detection, classification, owner routing, review, audit, delta scan, metrics, and evaluation responsibilities. |
| BEPLAN-003 | Review state transitions | The planning documents define success, failure, permission-denial, partial-data, and rollback paths. |
| BEPLAN-004 | Review safety constraints | The planning documents keep raw sensitive text out of public responses and keep deletion simulated. |
| BEPLAN-005 | Review contract compatibility | The planning documents use existing P0 endpoints and mock payload shapes without requiring a contract version bump. |
| BEPLAN-006 | Review primitive acceptance | The planning documents define observable acceptance criteria for each backend workflow stage. |

## Backend API Server Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| BEAPI-001 | Call `GET /api/health` | The server returns `data.ok = true`, contract metadata, and `X-Contract-Version = 0.1.0`. |
| BEAPI-002 | Call `GET /api/sources` | The response returns the mock-compatible source list including `source_001`. |
| BEAPI-003 | Start a full scan for `source_001` | The server returns `202`, a running scan envelope, `meta.partial = true`, and no raw source content. |
| BEAPI-004 | Start a full scan for a not-ready source | The server returns `application/problem+json` and does not create a new audit event. |
| BEAPI-005 | Record a valid review decision | The server returns `201`, updates finding status, creates a review audit event, and keeps `deletionExecuted = false`. |
| BEAPI-006 | Load the frontend with API unavailable | The frontend renders a server-unavailable or explicit development fallback state without silently presenting fake prelaunch data. |

## Prelaunch Account Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| AUTH-001 | Call `GET /api/auth/providers` | The response lists Google and GitHub with `configured` flags and no secrets. |
| AUTH-002 | Start login for an unconfigured provider | The server returns `application/problem+json` and creates no session. |
| AUTH-003 | Start GitHub login when configured | The server redirects to GitHub with state and PKCE challenge, and stores the verifier only in a signed HttpOnly transaction cookie. |
| AUTH-004 | Complete callback with mismatched state | The server rejects the callback before token exchange and creates no user or session. |
| AUTH-005 | Complete callback with validated provider identity | The server stores a local user profile, creates a first-party session, and redirects to the app. |
| AUTH-006 | Call `GET /api/auth/session` with a valid cookie | The response returns `authenticated = true`, safe user profile fields, and no provider tokens. |
| AUTH-007 | Call `POST /api/auth/logout` | The server revokes the local session, clears the cookie, and `/api/auth/session` returns unauthenticated. |
| AUTH-008 | Render unauthenticated console | The frontend shows the sign-in gate and does not render fixture findings. |
| AUTH-009 | Render authenticated console with no findings | The frontend shows operational empty states and source setup actions instead of fake examples. |
| AUTH-010 | Start server with `DATASENTINEL_ENABLE_DEMO_FIXTURES=false` | Sources, findings, audit, metrics, and evaluation start empty until a configured local source is scanned. |
| AUTH-011 | Restart a SQLite-backed preview after disabling demo fixtures | Historical seeded demo sources and workflow documents are removed while real registered local sources and account/session records remain. |

## Local SQLite Persistence Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| DB-001 | Run `python3 -m backend.datasentinel.db_tool init --db-path <file>` | A local SQLite file is created with schema version, source rows, and one workflow document. |
| DB-002 | Run `python3 -m backend.datasentinel.db_tool status --db-path <file>` | The command reports the database path, schema version, source count, and workflow-document count without exposing secrets. |
| DB-003 | Register a source through a SQLite-backed API app and restart with the same file | The source remains listed after restart. |
| DB-004 | Record a review through a SQLite-backed API app and restart with the same file | Finding status and the review audit event remain visible after restart. |
| DB-005 | Start the API without `--db-path` | The server keeps the existing in-memory fixture-backed behavior. |

## Prelaunch Source Input Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| SRCIN-001 | Call `GET /api/integrations/google-drive/picker-config` with a valid first-party session cookie | The response reports `configured`, `clientId`, `apiKey`, `appId`, scopes, and missing browser setup fields without returning client secrets or provider tokens. |
| SRCIN-002 | Register a direct HTTPS file link | The source is created as `remote_file_link` with `config.url` and can become scan-ready when the URL passes policy checks. |
| SRCIN-003 | Scan a direct HTTPS text file with detectable personal-data patterns | The scan produces findings with redacted evidence and no raw source body or unredacted personal data in public payloads. |
| SRCIN-004 | Register a non-HTTPS, credential-bearing, private-address, over-limit, or unsupported direct file link | The backend rejects the connection or scan before creating workflow output. |
| SRCIN-005 | Load an authenticated empty prelaunch project with no findings, then register a source | The frontend treats the API as available and does not request a blank finding detail before source registration. |
| SRCIN-006 | Select Google Drive files through Picker | The source stores selected item metadata and keeps the access token out of persisted source state. |
| SRCIN-007 | Select a Google Drive folder through Picker | The scan enumerates descendant files up to the prelaunch limit and exports supported Google Workspace documents to text-like content. |
| SRCIN-008 | Start a Google Drive scan without a per-scan access token | The backend returns `application/problem+json` and leaves scan, finding, audit, metric, and evaluation state unchanged. |
| SRCIN-009 | Review public payloads after remote-link or Drive scans | Payloads expose metadata, warnings, redacted snippets, findings, metrics, and audit events only; raw file bodies, provider tokens, refresh tokens, client secrets, legal conclusions, and deletion execution are absent. |

## OpenRouter AI Assistive Processing Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| AI-001 | Start backend without an OpenRouter key | `/api/health` reports `ai.status = disabled` or `missing_api_key`; no API key appears in the payload. |
| AI-002 | Start backend with assistive mode and a key | `/api/health` reports provider `openrouter`, the configured model, budget limits, fail-closed guard, and the metadata/text/OCR/grep/AI tier plan. |
| AI-003 | Plan a redacted ambiguous evidence candidate with deterministic anchors and policy-pack context | The tier plan runs source/policy context, metadata, text/OCR, grep, and policy-context/risk before marking `ai_context` ready. |
| AI-004 | Plan an unredacted evidence candidate | `ai_context` is blocked before any external request. |
| AI-005 | Preflight when usage plus estimated cost exceeds budget | The budget guard rejects the call and leaves scan, finding, audit, metrics, and evaluation state unchanged. |
| AI-006 | Preflight when OpenRouter usage cannot be checked | Fail-closed mode rejects the call before any prompt leaves the process. |
| AI-007 | Run normal full and delta scans | Existing deterministic paths still report `modelCalls = 0`, `estimatedCostUsd = 0`, no raw content exposure, no legal conclusion, and no deletion execution. |
| AI-008 | Review AI metadata against the Atlas | `/api/health` and `aiProcessing` include `atlasReference`, 12 `atlasAlignment` entries, and tier rows whose `atlasStages` cover source/policy, inventory/OCR, deterministic signal detection, context/risk, owner/review boundaries, audit, delta, admin metrics, and evaluation. |
| AI-009 | Attempt AI context support without deterministic anchors or policy-pack context | The request is rejected before any external model request. |

## Full Scan Start Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| FULLSCAN-001 | Start full scan from Dashboard | The workflow targets the default organizer sample source by `sourceId` and creates a running full scan. |
| FULLSCAN-002 | Start full scan from Sources row | The workflow targets the selected source by `sourceId`, not a hard-coded first source. |
| FULLSCAN-003 | Start full scan for not-ready source | No scan or audit event is created, and the user receives a neutral denial message. |
| FULLSCAN-004 | Observe running full scan metrics | Scan progress, scanned files, flagged files, scanned volume, and scan status update together. |
| FULLSCAN-005 | Complete simulated full scan | Scan progress reaches 100%, duration and throughput are set, metrics match the completed scan, and evaluation points to the completed scan. |
| FULLSCAN-006 | Review full scan audit events | Start and completion events include scan ID, actor/system attribution, timestamp, source summary, and no raw sensitive content. |
| FULLSCAN-007 | Verify P0 cost boundary | Full scan start uses deterministic fixture data with zero model calls and no paid external services. |

## Source Inventory and Content Extraction Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| INVEXT-001 | Start full scan for the organizer sample source | The running scan includes file-inventory and content-extraction summaries for `source_001`. |
| INVEXT-002 | Observe running inventory and extraction | The workflow marks partial data, exposes recoverable warnings, and shows stage progress without raw content. |
| INVEXT-003 | Complete full scan extraction | Inventory and extraction stages become complete, final counts match the scan profile, and warnings remain countable. |
| INVEXT-004 | Verify raw-content boundary | `rawContentExposed` remains `false` and no public payload contains raw extracted text, full file bodies, or page images. |
| INVEXT-005 | Verify unsupported-file handling | Unsupported or OCR-deferred files are counted as recoverable warnings and do not block scan completion. |
| INVEXT-006 | Verify resource and cost boundary | Evaluation resource intensity keeps model calls and estimated paid-service cost at zero. |
| INVEXT-007 | Reject inventory for not-ready source | A not-ready source cannot create scan, inventory, extraction, or audit state changes. |

## Deterministic Signal Detection Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| SIGNAL-001 | Start a full scan | The running scan includes `signalDetection.status = pending` and the `detecting_signals` stage after `extracting_content`. |
| SIGNAL-002 | Complete a full scan | The completed scan includes detector rules version/hash, evidence requirements, evaluated evidence candidates, detected/redacted signal counts, findings-with-signals count, and signal-type counts. |
| SIGNAL-003 | Verify redaction boundary | Finding details expose only redacted signal snippets and no public payload contains raw extracted text, full file bodies, page images, or unredacted personal data. |
| SIGNAL-004 | Verify policy evidence requirements | `signalDetection.evidenceRequirements` matches the active policy pack evidence requirements when available. |
| SIGNAL-005 | Verify evaluation traceability | Evaluation stores the signal-detection rules hash and includes `signal_detection:completed` in the quality-basis input stages. |
| SIGNAL-006 | Verify resource and cost boundary | Signal detection keeps model calls and estimated paid-service cost at zero. |
| SIGNAL-007 | Reject signal detection for not-ready source | A not-ready source cannot create scan, extraction, signal-detection, finding, audit, metric, or evaluation state changes. |

## Context and Risk Judgment Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| CTXRISK-001 | Start a full scan | The running scan includes `contextRisk.status = pending` and the `judging_context_risk` stage after `detecting_signals`. |
| CTXRISK-002 | Complete a full scan | The completed scan includes a completed `contextRisk` summary with assessed evidence, context, risk, retention-review, and human-review counts. |
| CTXRISK-003 | Verify policy-pack traceability | `contextRisk.policyPackVersion` matches the active governance policy pack and evaluation stores a context-risk rules hash. |
| CTXRISK-004 | Verify legal boundary | `legalConclusionProvided` remains `false`, and UI-facing copy does not present the automated judgment as legal advice. |
| CTXRISK-005 | Verify raw-content boundary | Context/risk warnings and summaries do not contain raw extracted text, file bodies, page images, or unredacted personal data. |
| CTXRISK-006 | Verify resource and cost boundary | Context/risk judgment keeps model calls and estimated paid-service cost at zero. |
| CTXRISK-007 | Reject context/risk for not-ready source | A not-ready source cannot create scan, inventory, extraction, signal-detection, context/risk, or audit state changes. |

## Owner Routing and Assignment Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| OWNROUTE-001 | Start a full scan | The running scan includes `ownerAssignment.status = pending` and the `assigning_owner` stage after `judging_context_risk`. |
| OWNROUTE-002 | Complete a full scan | The completed scan includes a completed `ownerAssignment` summary with assigned, direct-owner, Master of Data fallback, escalation, and unowned counts. |
| OWNROUTE-003 | Verify accountability traceability | `ownerAssignment.policyPackVersion` and `organizationModelVersion` match governance config, and evaluation stores an owner-assignment rules hash. |
| OWNROUTE-004 | Verify no silent unowned findings | Completed controlled fixtures expose `unownedFindings = 0`; missing owner metadata must degrade to fallback or escalation. |
| OWNROUTE-005 | Verify audit visibility | Owner routing completion creates an audit-visible event with actor, timestamp, routed counts, and policy-pack version. |
| OWNROUTE-006 | Verify raw-content boundary | Owner-routing warnings and summaries do not contain raw extracted text, file bodies, page images, directory secrets, or unredacted personal data. |
| OWNROUTE-007 | Verify resource and cost boundary | Owner routing keeps model calls and estimated paid-service cost at zero. |
| OWNROUTE-008 | Reject owner routing for not-ready source | A not-ready source cannot create scan, inventory, extraction, context/risk, owner-assignment, or audit state changes. |

## Finding Assembly and Evidence Card Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| FINDASM-001 | Start a full scan | The running scan includes `findingAssembly.status = pending` and the `assembling_findings` stage after `assigning_owner`. |
| FINDASM-002 | Complete a full scan | The completed scan includes a completed `findingAssembly` summary with assembled findings, evidence cards, redacted signals, missing-card count, denied-action count, and policy-pack version. |
| FINDASM-003 | Verify scan continuity | Completed finding rows and details use the completed scan ID and are generated from previous stage summaries instead of disconnected static rows. |
| FINDASM-004 | Verify evidence-card completeness | Every assembled finding detail has at least one redacted signal, policy context, owner assignment, retention status, action boundary, and audit timeline. |
| FINDASM-005 | Verify no legal conclusion | `legalConclusionProvided` remains `false`, and UI-facing copy presents evidence cards as human-review support. |
| FINDASM-006 | Verify raw-content boundary | Evidence snippets do not expose raw extracted text, file bodies, page images, unredacted personal data, or full financial identifiers. |
| FINDASM-007 | Verify ownerless fallback | Missing source owner metadata routes evidence cards to escalation instead of leaving findings unowned. |
| FINDASM-008 | Verify audit and evaluation traceability | Finding assembly creates an audit-visible event and evaluation stores a finding-assembly rules hash. |
| FINDASM-009 | Verify resource and cost boundary | Finding assembly keeps model calls and estimated paid-service cost at zero. |
| FINDASM-010 | Reject assembly for not-ready source | A not-ready source cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, finding, evidence-card, or audit state changes. |

## Review Support and Permission Boundary Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| REVIEW-001 | Start a full scan | The running scan includes `reviewSupport.status = pending` and the `preparing_review_support` stage after `assembling_findings`. |
| REVIEW-002 | Complete a full scan | The completed scan includes a completed `reviewSupport` summary with supported finding count, decision count, reason count, checklist count, transfer count, escalation count, denied action count, and policy-pack version. |
| REVIEW-003 | Verify finding-specific support | Review support for an assembled finding includes allowed decisions, checklist items, transfer options, escalation options, and permission-boundary denial reasons derived from governance data. |
| REVIEW-004 | Verify all P0 decisions | Allowed reviewer support can show `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate`. |
| REVIEW-005 | Verify reason requirement | Every available review decision requires a human reason before submission. |
| REVIEW-006 | Verify permission denial | A denied actor receives no review decisions and a review attempt is rejected without state changes. |
| REVIEW-007 | Verify target validation | Reassign and escalate decisions require a target owner or escalation queue. |
| REVIEW-008 | Verify no real deletion | `execute_real_deletion` remains a denied action with a visible reason. |
| REVIEW-009 | Verify audit and evaluation traceability | Review support exposes a rules hash that evaluation preserves while keeping model calls and estimated paid-service cost at zero. |
| REVIEW-010 | Verify raw-content boundary | Review support does not expose raw extracted text, file bodies, page images, credentials, hidden permission data, or unredacted personal data. |
| REVIEW-011 | Reject support for not-ready source | A not-ready source cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, review-support, permission-boundary, finding, evidence-card, or audit state changes. |

## Human Review Decision Handling Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| HREV-001 | Submit allowed delete candidate decision | The finding status becomes `delete_candidate`, one review record and one audit event are created, and `deletionExecuted` remains `false`. |
| HREV-002 | Submit allowed retain decision | The finding status becomes `retained`, the reason and retention review date are recorded, and no source file is changed. |
| HREV-003 | Submit false positive correction | The finding status becomes `false_positive`, the reason is preserved for audit and evaluation context, and detector rules are not changed. |
| HREV-004 | Submit owner reassignment | The finding status remains reviewable as `assigned`, the delegated owner is recorded, and the audit event names the transfer target. |
| HREV-005 | Submit escalation | The finding status becomes `escalated`, the escalation queue is recorded, and the audit event names the queue target. |
| HREV-006 | Reject denied actor or denied decision | No finding, source, audit, metric, or evaluation state changes. |
| HREV-007 | Reject missing reason or checklist acknowledgement | No finding, source, audit, metric, or evaluation state changes. |
| HREV-008 | Reject retain without retention review date | No finding, source, audit, metric, or evaluation state changes. |
| HREV-009 | Reject transfer or escalation without supported target | No finding, source, audit, metric, or evaluation state changes. |
| HREV-010 | Repeat command with same idempotency key | The command is treated as already accepted and does not create duplicate audit events or metric increments. |
| HREV-011 | Verify audit and metrics | Accepted decisions include actor, timestamp, decision, reason, resulting status, policy-pack version, permission-boundary fingerprint, review-support rules fingerprint, backlog movement, and outcome counters. |
| HREV-012 | Verify evaluation and cost boundary | Human-review decision handling preserves a rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost. |

## Audit Event Recording Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| AUDIT-001 | Complete a full scan | The scan pipeline ends with `recording_audit_events`, and the audit summary counts scan, finding, system, and human events without raw content exposure. |
| AUDIT-002 | Review global audit list after scan completion | Scan start, scan completion, owner assignment, finding assembly, finding assembled, and finding assigned events use the same structured audit-event shape. |
| AUDIT-003 | Submit an accepted review decision | The finding timeline, global audit list, scan audit summary, audit metrics, and evaluation traceability update together. |
| AUDIT-004 | Submit a review reason containing obvious sensitive values | Public audit reason text masks emails, IBAN-like values, long numbers, and control characters. |
| AUDIT-005 | Submit denied, incomplete, stale, unknown, or duplicate commands | No duplicate audit events or audit metric increments are created. |
| AUDIT-006 | Review deletion boundary | Audit events may record `delete_candidate`, but `deletionExecuted` remains `false` and no source-file, connector, retention-label, or access-control mutation occurs. |

## Incremental Delta Scan Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| DELTA-001 | Start delta scan from completed full-scan baseline | The selected scan-ready source creates a running delta scan with baseline ID, source snapshot, inventory fingerprint, changed counts, partial warnings, and a `delta_scan_started` audit event. |
| DELTA-002 | Start delta scan without completed baseline | No scan, audit, finding, metric, or evaluation state changes, and the user receives a neutral baseline-unavailable message. |
| DELTA-003 | Start delta scan with mismatched explicit baseline | The command is rejected without state changes. |
| DELTA-004 | Observe running delta pipeline | The pipeline exposes `comparing_delta_baseline` before changed-file inventory and extraction. |
| DELTA-005 | Complete delta scan | Only changed files are processed, changed findings use the delta scan ID, unchanged files are carried forward, and missing files are represented as inventory changes. |
| DELTA-006 | Verify no deletion boundary | `missingFilesTreatedAsDeleted` and `deletionExecuted` remain `false`, and no audit event executes real deletion. |
| DELTA-007 | Verify downstream continuity | Completed delta output updates context/risk, owner routing, finding assembly, review support, audit recording, metrics, and evaluation together. |
| DELTA-008 | Verify evaluation and cost boundary | Evaluation preserves a delta rules hash, deterministic reproducibility, throughput, zero model calls, and zero estimated paid-service cost. |

## Admin Metrics Aggregation Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| METRICS-001 | Start a full scan | Running metrics include `aggregation.status = partial`, upstream input-stage statuses, scan coverage, risk, owner, audit, safety, and zero-cost fields. |
| METRICS-002 | Complete a full scan | Completed metrics aggregate scan coverage, risk queue, owner backlog, review outcomes, audit evidence, evaluation linkage, and resource cost from prior stage summaries. |
| METRICS-003 | Complete a delta scan | Delta aggregate metrics include baseline, changed, processed, carried-forward, and missing counts while keeping `missingFilesTreatedAsDeleted = false` and `deletionExecuted = false`. |
| METRICS-004 | Submit an accepted review decision | Owner backlog, outcome counters, audit counts, throughput inputs, and evaluation-linked aggregation update exactly once. |
| METRICS-005 | Reject scan or review command | Metrics remain unchanged together with source, finding, audit, and evaluation state. |
| METRICS-006 | Verify safety and cost boundary | Aggregation keeps raw-content, legal-conclusion, deletion-execution, model-call, and estimated-cost boundaries visible and safe. |
| METRICS-007 | Verify reproducibility | Evaluation stores `adminMetricsRulesHash` matching the metrics aggregation fingerprint. |
| METRICS-008 | Review Dashboard management indicators | Dashboard displays owner completion, risk queue, audit evidence, metric basis, and cost without raw source content or legal conclusions. |

## Evaluation Metrics Generation Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| EVALGEN-001 | Complete a full scan | Evaluation computes precision, recall, F1, reproducibility, throughput, resource intensity, confusion-matrix counts, scenario-level metrics, review-throughput context, risk-progress fields, and an evaluation-rules fingerprint. |
| EVALGEN-002 | Verify upstream traceability | Evaluation preserves dataset hash, scanner version, detector rules, config hash, policy-pack version, context/risk, owner, finding, review-support, audit, admin-metrics, and finding fingerprints. |
| EVALGEN-003 | Verify scenario-level quality | Scenario metrics expose per-family precision, recall, F1, false positives, false negatives, unsupported-file context, and OCR-deferred context where available. |
| EVALGEN-004 | Complete a delta scan | Evaluation computes changed-file quality context and preserves baseline, carried-forward, missing-file, and no-deletion boundaries. |
| EVALGEN-005 | Submit an accepted review decision | Review-throughput and risk-progress evaluation fields refresh exactly once while scan-quality precision, recall, and F1 remain stable. |
| EVALGEN-006 | Reject scan or review command | Evaluation remains unchanged together with metric, audit, source, and finding state. |
| EVALGEN-007 | Verify safety and cost boundary | Evaluation keeps raw-content, legal-conclusion, deletion-execution, model-call, estimated-cost, and paid-service boundaries visible and safe. |
| EVALGEN-008 | Review Evaluation page | The page renders scan quality, confusion matrix, scenario metrics, resource intensity, reproducibility, and safety boundaries without raw source content or legal conclusions. |

## File Review Editor Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| FILEREVIEW-001 | Open file review from Finding Detail | The editor opens for the finding file and focuses the first available redacted evidence anchor. |
| FILEREVIEW-002 | Open file review from an evidence card | The editor opens with that evidence anchor selected. |
| FILEREVIEW-003 | Select another evidence anchor | The active redacted preview highlight changes to the selected anchor. |
| FILEREVIEW-004 | Review redaction boundary | The editor shows masked snippets and fallback location labels without raw sensitive values or file bodies. |
| FILEREVIEW-005 | Close file review | The user returns to Finding Detail without changing scan, finding, source-file, or review state. |

## Public Homepage Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| HOME-001 | Visit `/` | The public project homepage renders without the internal app shell. |
| HOME-002 | Open dashboard from homepage | The user navigates to `/dashboard`, and the internal app shell dashboard renders. |
| HOME-003 | Scroll homepage | Parallax layers move when reduced motion is not requested, while content remains readable. |
| HOME-004 | Review homepage claims | The page explains discovery, evidence, routing, review, audit, governance, and evaluation without claiming full legal compliance. |

## Remote Preview Deployment Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| DEPLOY-001 | Build frontend for remote preview | `npm run build` completes successfully before upload. |
| DEPLOY-002 | Visit `https://founder-force.uk/` | Caddy returns the DataSentinel frontend HTML from the active release after DNS points to `agent-us`. |
| DEPLOY-003 | Visit `https://founder-force.uk/dashboard` directly | Caddy falls back to `index.html`, and the frontend can render the dashboard route after DNS points to `agent-us`. |
| DEPLOY-004 | Call `https://founder-force.uk/api/health` | Caddy proxies to the loopback P0 API server and returns a contract health envelope. |
| DEPLOY-005 | Review remote service boundary | The preview exposes only static frontend assets plus the P0 API, may use the approved local SQLite state file, and does not start OAuth, Microsoft Graph, tenant, production database, queue, production connector, or deletion services. |
| DEPLOY-006 | Review rollback path | A saved Caddyfile backup, release symlink, and removable API service make rollback possible without changing product code. |

## Future Behavior Test Themes

These are not implementation tests yet. They define the areas that future tests should cover:

- App shell behavior for page-title-focused top bar, top-right notifications, top-left workspace menu visibility, bottom-left account menu visibility, sidebar collapse, menu open, keyboard close, and platform-status display.
- Public homepage behavior for root-route rendering, dashboard navigation, scroll-linked parallax, and reduced-motion fallback.
- File review behavior for format-specific anchors, renderer fallback, keyboard navigation, and redacted preview highlighting.
- Full-scan behavior with controlled sample files.
- Classification behavior for GDPR-relevant evidence.
- Owner-routing behavior when owner metadata is present or missing.
- Human-review decisions for delete, retain, mask, archive, and escalate.
- Audit-event behavior for every visible state transition.
- Delta-scan behavior for unchanged, changed, new, and deleted files.
- Evaluation behavior for precision, recall, F1, reproducibility, throughput, and resource intensity.
- Governance behavior for policy-pack changes, org model changes, task transfers, and permission boundaries.
