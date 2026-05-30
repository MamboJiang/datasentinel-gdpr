# Backend Post-Source Execution Plan

## Problem Definition

The team has made progress on connecting the controlled sample source. The next risk is treating the remaining backend work as one broad scanner task instead of a sequence of observable, testable steps.

This design turns the post-source backend path into a planning contract. It does not approve implementation code, runtime dependencies, production storage, live Microsoft Graph access, real deletion, or a new API shape. It explains how the backend should move from a connected sample source to a measurable, evidence-backed, human-reviewed, audit-ready P0 workflow.

## Scope

In scope:

- Full scan planning after a sample source is connected.
- Finding detection, evidence assembly, owner routing, review handling, audit logging, delta scan planning, admin metrics, and evaluation planning.
- Step boundaries, state transitions, failure paths, rollback paths, and primitive acceptance criteria.
- Use of the existing contract endpoints and mock payload shapes.

Out of scope:

- Runtime framework selection.
- Database, queue, worker, OCR, AI model, or parser selection.
- Production authentication or authorization.
- Production Microsoft Graph integration.
- Real deletion, quarantine, or remote file mutation.
- Legal advice or hard-coded legal conclusions.

## Research Basis

- The existing project contract uses OpenAPI 3.1, JSON Schema tolerance, and RFC 9457 problem details as documented in `docs/API_CONTRACT.md`.
- The official GDPR text and European Commission guidance support treating data minimisation, storage limitation, integrity, confidentiality, and accountability as governance concerns rather than scanner-only concerns. This design therefore keeps legal and retention details in versioned policy packs and requires human review before deletion decisions.

References:

- `docs/API_CONTRACT.md`
- `docs/GOVERNANCE_CONFIG.md`
- `docs/EVALUATION.md`
- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- European Commission GDPR principles overview: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en

## Design Requirements

- Preserve the existing source -> scan -> finding -> review -> audit -> delta -> evaluation loop.
- Keep every step observable through the existing P0 contract or mock fixtures.
- Produce evidence for each finding before risk or owner decisions are shown.
- Keep sensitive evidence redacted at API and UI boundaries.
- Use deterministic detection before AI-assisted explanations.
- Route findings to accountable owners or escalation queues.
- Require human actor, reason, permission context, and policy-pack version for review decisions.
- Keep deletion simulated as `delete_candidate`.
- Make partial data explicit through `meta.partial` and warnings.
- Let frontend and backend continue parallel delivery through the current tolerant contract.

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Build every backend stage before integration | Complete mental model | High integration risk and late feedback | Rejected |
| Implement only static mock returns | Fast demo fallback | Does not prove scan, review, audit, or evaluation behavior | Rejected as final path |
| Build one vertical slice after source connection | Proves the full governance loop with controlled scope | Requires discipline to avoid broad parser or policy work | Accepted |
| Add new endpoints for each internal stage | Easy debugging | Expands public contract before necessary | Rejected for P0 |
| Keep stages internal and expose existing P0 endpoints | Stable contract and lower frontend churn | Needs clear internal planning | Accepted |

## Backend Step Plan Summary

Detailed stage contracts are documented in `docs/design/backend-post-source-stage-details.md`. The approved planning order is:

| Step | Stage | Purpose |
| --- | --- | --- |
| 1 | Full scan orchestration | Create and observe a scan after a sample source is connected. |
| 2 | Source inventory and extraction planning | Build file candidates without exposing raw content. |
| 3 | Deterministic signal detection | Produce redacted evidence before risk or AI-assisted explanation. |
| 4 | Context classification and risk planning | Explain context, risk, and retention from evidence and policy guidance; the P0 implementation slice is documented in `docs/design/context-risk-judgment.md`. |
| 5 | Owner routing | Assign each finding to a direct owner, fallback owner, or escalation path. |
| 6 | Finding assembly and evidence card | Compose contract-compatible list and detail responses; the P0 implementation slice is documented in `docs/design/finding-assembly-evidence-card.md`. |
| 7 | Review support and permission boundary | Show allowed actions, denied actions, checklist, and reason requirements; the P0 implementation slice is documented in `docs/design/review-support-permission-boundary.md`. |
| 8 | Human review command handling | Record accountable decisions without real deletion. |
| 9 | Audit event logging | Preserve scan, assignment, and review history. |
| 10 | Delta scan planning | Compare changed files against a prior full-scan baseline. |
| 11 | Admin metrics aggregation | Expose progress, risk, backlog, volume, and time metrics. |
| 12 | Evaluation run planning | Publish accuracy, reproducibility, throughput, and resource intensity. |

## Sample Scenario Mapping

| Sample family | Likely evidence planning | Context planning | Owner routing planning | Review planning |
| --- | --- | --- | --- | --- |
| `Expense_Report` | Employee or vendor identifiers, email, reimbursement data | Expense or finance record | Direct owner when metadata exists; finance Master of Data fallback | Retention review or keep with reason |
| `IT_Access_Request` | Employee ID, email, access role, requester or approver | Access management record | IT owner or direct requester; escalation if stale privileged access appears | Delete candidate, reassign, or escalate |
| `Incident_Report` | Contact details, incident participants, free-text descriptions | Incident or support record | Responsible department owner; privacy escalation when context is sensitive | Escalate or keep with reason |
| `Supplier_Onboarding` | Billing address, email, IBAN-like pattern, signature | Supplier onboarding record | Supplier process owner or finance Master of Data fallback | Escalate or keep with reason |
| `Training_Evaluation` | Employee names, emails, feedback comments | HR or training record | HR or training owner; fallback to Master of Data | Retention review or false positive correction |

These mappings are planning assumptions for controlled demo scenarios. They are not legal conclusions and must be represented through policy-pack guidance.

## End-to-End State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Source connected | Full scan requested | Source adapter is mock-ready or readable | Scan queued | Create scan record |
| Scan queued | Worker starts scan | Scan is not cancelled | Inventorying files | Record scan started |
| Inventorying files | Inventory completes | At least one candidate exists | Extracting evidence | Store file fingerprints |
| Inventorying files | Inventory fails | Failure is blocking | Scan failed | Return problem details and audit scan failure |
| Extracting evidence | File parsed | Evidence candidate exists | Detecting signals | Keep raw text inside backend boundary |
| Extracting evidence | File unsupported | Failure is recoverable | Partial scan | Add warning and continue |
| Detecting signals | Signal found | Signal can be redacted | Classifying context | Store redacted evidence signal |
| Detecting signals | No signal found | File scanned successfully | No finding | Increment scanned count |
| Classifying context | Context assigned | Policy pack is active | Routing owner | Attach policy-pack version |
| Routing owner | Owner resolved | Owner confidence is sufficient | Finding assigned | Record owner assignment event |
| Routing owner | Owner unresolved | Escalation path exists | Finding escalated | Queue privacy or legal review |
| Finding assigned | Reviewer opens support | Actor has read permission | Review supported | Return checklist and actions |
| Finding assigned | Review support prepared | Finding assembly is complete | Permission boundary visible | Return allowed actions, denied actions, and denial reasons |
| Review supported | Review submitted | Actor is allowed and reason exists | Review recorded | Create audit event |
| Review supported | Review denied | Actor lacks permission | Review rejected | Return problem details with denial reason |
| Review recorded | Finding status updated | Decision is terminal or routed | Audit visible | Update finding detail and audit timeline |
| Audit visible | Delta scan requested | Full-scan baseline exists | Delta scan queued | Compare file fingerprints |
| Delta scan completed | Evaluation requested | Metrics inputs exist or mock values are allowed | Evaluation visible | Publish latest evaluation run |

## Failure and Recovery Planning

| Failure | Required behavior |
| --- | --- |
| Source becomes unreadable after connection | Mark scan failed or partial, return problem details or warning, and keep prior findings intact. |
| File cannot be parsed | Continue scan when recoverable, count warning, and avoid raw text exposure. |
| Detector emits low-confidence signal | Keep finding neutral or require human review; do not claim legal conclusion. |
| Owner cannot be resolved | Use Master of Data fallback or escalation path; never leave finding silently unowned. |
| Reviewer lacks permission | Return denied action before submit where possible; reject denied submit with problem details. |
| Duplicate review request | Use idempotency key to avoid conflicting audit events. |
| Policy pack changes after review | Preserve historical policy context; represent affected decisions as reopen candidates only if the contract supports it. |
| Delta scan sees missing file | Treat as source inventory change, not DataSentinel deletion. |
| Evaluation inputs incomplete | Return partial evaluation with warnings or deterministic mock values for P0. |

## Rollback Path

If the full post-source plan is too large for the first backend implementation:

1. Keep `/api/sources`, `/api/scans/full`, `/api/scans/{scanId}`, `/api/findings`, `/api/findings/{findingId}`, `/api/findings/{findingId}/review`, and `/api/audit/events` as the first vertical slice.
2. Use deterministic fixture-backed detection for one sample family.
3. Return contract-compatible mock values for governance, permissions, metrics, and evaluation.
4. Keep delta scan as a represented scan type until file fingerprint comparison is implemented.
5. Do not expand the public contract unless the team approves a versioned contract change.

## Primitive Acceptance Criteria

- A connected sample source can start a full scan without introducing a new public endpoint.
- A scan status can expose progress, counts, and failure or partial warnings.
- A finding cannot be created without redacted evidence.
- A finding can show context, risk, owner, policy-pack version, retention status, and audit timeline.
- Owner routing can choose direct owner, Master of Data fallback, or escalation without silently dropping ownership.
- Review support can show allowed actions, denied actions, required reasons, transfer options, and escalation options before submit.
- A review decision cannot be recorded without actor and reason.
- A delete decision is represented only as `delete_candidate` in P0.
- Every review decision creates one audit event that preserves actor, timestamp, decision, reason, resulting status, and policy context.
- A delta scan can compare changed files against a prior full-scan baseline.
- Admin metrics can show scanned files, flagged files, scanned volume, progress, scan time, review backlog, high-risk count, and retention-overdue count.
- Evaluation can show precision, recall, F1, reproducibility, throughput, and resource intensity.
- Partial data is explicit through `meta.partial` and warnings rather than hidden or silently omitted.
- The plan remains compatible with `contracts/openapi.yaml` and existing mock fixtures.
