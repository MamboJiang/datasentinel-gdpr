# Full Scan Start Workflow

## Problem Definition

The P0 demo needs the first post-source step to behave like a real workflow handoff: a user selects a controlled, mock-ready source and starts a full scan that becomes visible through scan status, admin metrics, audit events, and evaluation readiness.

This design covers the current implementation slice only. It does not approve production Microsoft Graph access, OAuth, tenant integration, remote file mutation, automatic deletion, a new public endpoint, or a broad scanner pipeline.

## Design Inputs

- `docs/PROJECT_CONTEXT.md` defines the core loop as source connection -> full scan -> detection -> review -> audit -> delta scan -> evaluation.
- `docs/API_CONTRACT.md` and `contracts/openapi.yaml` already define `POST /api/scans/full`, `GET /api/scans/{scanId}`, `GET /api/admin/metrics`, and audit/evaluation surfaces.
- `docs/GOVERNANCE_CONFIG.md` requires policy packs, source adapter readiness, visible permission boundaries, and no hard-coded legal snapshot.
- `docs/design/backend-post-source-stage-details.md` defines Step 1 as full scan orchestration after a connected sample source exists.
- Official GDPR guidance supports data minimisation, storage limitation, integrity, confidentiality, and accountability as governance concerns, so scan start must be observable and audit-friendly without making legal conclusions.

References:

- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- European Commission GDPR principles overview: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en
- Vitest documentation for Vite-compatible test execution: https://vitest.dev/

## Scope

In scope:

- Start a simulated full scan from the default organizer sample source when it is `mock_ready`.
- Start a simulated full scan from the Sources page only when the chosen source is scan-ready.
- Keep the request model aligned with the contract by using an explicit `sourceId`.
- Require current actor context, idempotency context when available, source readability/readiness, and the active policy-pack version before creating scan state.
- Update scan status, progress, admin metrics, audit events, and evaluation summary in the mock data layer.
- Add behavior tests for source readiness, default source selection, running scan state, completion state, metrics, audit events, and denied start attempts.

Out of scope:

- Downloading or vendoring organizer sample files.
- OCR, PDF parsing, embeddings, paid model calls, or AI classification.
- Persistent storage, queues, workers, authentication, authorization, or production source connectors.
- Real deletion or remote file mutation.
- Public API contract expansion.

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Keep the existing button-only local state change | Fast | Does not prove handoff from source readiness to scan status | Rejected |
| Add production backend orchestration now | Closer to final architecture | Expands runtime, storage, and worker decisions before acceptance | Rejected |
| Use a fixture-backed vertical slice with tested workflow logic | Contract-compatible, reversible, low cost, demoable | Still simulated until backend exists | Accepted |
| Add a new public scan endpoint for demo needs | Easy to tailor to UI | Breaks contract discipline | Rejected |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Source listed | Full scan requested | Source exists, current actor is present, idempotency context is stable, active policy pack is known, and status is `mock_ready` | Full scan running | Create scan record, attach policy context, set partial metrics, record `full_scan_started` audit event |
| Source listed | Full scan requested | Source missing or not scan-ready | Source listed | Reject start in UI/mock layer and show a neutral denial message |
| Full scan running | Duplicate full scan requested | Same scan is already running | Full scan running | Do not create a conflicting scan record |
| Full scan running | Simulated completion reached | Scan was not replaced by another scan | Full scan completed | Set progress to 1, set duration and throughput, record `full_scan_completed`, refresh evaluation summary |
| Full scan running | Delta scan requested | Existing scan can be replaced in mock mode | Delta scan running | Cancel current timer and start delta scan simulation |

Failure and partial paths:

- Missing or not-ready sources are blocked before a scan record is created.
- If a future backend returns partial scan data, the UI must render available values with `meta.partial` and warnings.
- Raw file content and unredacted sensitive snippets must not cross the public contract boundary.
- Deletion remains represented only as a later human `delete_candidate` review decision.

## Impact Surface

- `frontend/src/data/*`: mock workflow state transitions and testable scan logic.
- `frontend/src/pages/DashboardPage.tsx`: default full-scan source handoff.
- `frontend/src/pages/SourcesPage.tsx`: source-specific scan start and readiness guard.
- `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, and `ACCEPTANCE.md`: implementation acceptance, design, and validation updates.
- `frontend/package.json` and lockfile: add a Vite-compatible test runner.

## Rollback Path

Revert the workflow helper, page wiring, test files, and Vitest dependency. The original static mock payloads and existing public API contract remain valid because this slice does not change contract version, endpoint names, required fields, or mock fixture IDs.

## Primitive Acceptance Criteria

- The Dashboard start action targets the default organizer sample source by `sourceId`.
- The Sources table starts a full scan for the clicked source, not always the first source.
- Only readable or P0 `mock_ready` sources can start the full scan simulation, and the start command includes current actor, active policy-pack context, and idempotency context when available.
- Starting a full scan creates a running scan with progress, scanned-file count, flagged-file count, scanned volume, and a scan-start audit event.
- Completing the simulated full scan updates progress to 100%, duration, throughput, scanned totals, evaluation scan ID, and a scan-completion audit event.
- A not-ready source cannot create a scan or audit event.
- The implementation does not expose raw sensitive content, does not make legal conclusions, does not call paid AI services, and does not perform deletion.
- Behavior tests cover accepted and rejected scan-start paths.
