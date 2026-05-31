# Workspace Read Model Refresh

## Problem

Connected console sessions can keep stale Workspace-scoped read data after another member starts or completes a scan, changes Workspace members or groups, updates Source ownership, or records review activity. The visible result is stale dashboard progress, premature scan-completion feedback, Workspace admin lists that require manual browser refresh, and finding detail routes that render only summary fields.

## Basis

This design uses the existing P0 read endpoints documented in `docs/API_CONTRACT.md` and `contracts/openapi.yaml`. It does not add a websocket, server-sent events, queue, production tenant integration, external dependency, or new public API field.

## Options

| Option | Tradeoff |
| --- | --- |
| Manual refresh only | Lowest implementation cost, but keeps the stale multi-user behavior. |
| Periodic read-model refresh over existing GET endpoints | Uses current contract and is reversible; latency is bounded by the polling interval. |
| Push transport with websocket or SSE | Lower latency, but adds a new mechanism, server lifecycle, and deployment surface not needed for P0. |

The selected option is periodic read-model refresh over existing GET endpoints.

## State Machine

`disconnected -> checking -> connected -> background_refreshing -> connected`

Events:

- `initial_load_success`: stores the full read model and marks the project server connected.
- `initial_load_failure`: marks the project server disconnected and uses local mocks only when explicitly enabled.
- `refresh_tick`: reads the current Workspace-scoped sources, scan, findings, audit events, metrics, evaluation, governance, permission boundary, Workspace directory, and Workspace admin summary.
- `scan_running`: shortens the refresh interval while the current scan is running.
- `scan_completed_transition`: emits a completion notification only when the previous visible scan had the same `scanId` and `status = running`, and the refreshed scan has `status = completed`.
- `refresh_failure`: marks the project server disconnected.
- `finding_detail_route_opened`: reads `/findings/{findingId}` and caches the full detail for that route.

Guards:

- Background refresh only runs while the project server is connected.
- A completion notification requires an observed `running -> completed` transition for the same scan ID.
- Cached finding details are retained only for currently visible finding IDs.

Side effects:

- Background refresh updates the shared frontend data context without creating audit records.
- Scan-completion notification is session-local and does not replace backend audit events.
- Finding detail loading updates only the frontend cache for the requested finding.

Failure paths:

- If background refresh fails, the server status becomes disconnected and automatic refresh stops until the next successful server load path.
- If finding detail loading is rejected, the page keeps the available summary or cached detail and surfaces the problem message.

Rollback path:

Remove the polling effect and finding-detail route load, returning the console to explicit mutation refresh and primary-finding preloading. No contract or persisted state migration is required.

## Impact Surface

- Frontend shared data provider refresh cadence and notification condition.
- Dashboard latest-scan loading indicator and progress update behavior.
- Finding detail route cache loading by finding ID.
- Workspace admin/member/group and operational surfaces that consume the shared read model.

No backend schema, API field, permission model, source-file deletion behavior, or production integration changes are introduced.

## Primitive Acceptance Criteria

- A connected console session refreshes Workspace-scoped read data without requiring a manual browser refresh.
- While a scan is running, the Dashboard latest-scan panel visually indicates active loading and refreshes progress/status from the server.
- A scan-completion notification appears only after the client observes the same scan transition from `running` to `completed`.
- A still-running scan never creates a scan-completed notification.
- Opening `/findings/{findingId}` loads that finding's full detail by ID when the backend is connected.
- Finding detail remains safe when optional detail fields are missing: it shows neutral empty states rather than raw source data or blank uncontrolled regions.
- The refresh mechanism does not expose raw source content, provider tokens, legal conclusions, or deletion execution.
