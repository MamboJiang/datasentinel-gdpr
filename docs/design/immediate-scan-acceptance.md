# Immediate Scan Acceptance

## Problem

Prelaunch scans currently read source content before `POST /api/scans/full` or `POST /api/scans/delta` returns. Slow local folders, remote files, or Google Drive downloads delay the accepted response, so the UI cannot show that scanning has started until source reads finish.

## Options

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep synchronous scan execution | No state change | Slow command feedback | Rejected |
| Return `queued` and require a durable worker | Stronger restart semantics | Adds a production queue outside P0 scope | Rejected |
| Persist `running` immediately and complete in an in-process worker | Immediate user-visible acknowledgement with the existing contract | In-flight work is not durable across process restart | Accepted |

## State Machine

States:

- `idle`
- `running`
- `completed`
- `failed`

Events and guards:

- `start_scan_requested`: requires a valid `sourceId`, a scan-ready source, and required authorization for the source type.
- `scan_worker_completed`: stores or applies findings, metrics, evaluation, and audit events only when the active persisted scan still has the same `scanId`.
- `scan_worker_failed`: records a failed scan only when the active persisted scan still has the same `scanId`.
- `source_deleted`: clears the active workflow when the deleted source owns the running scan.

Transitions:

- `idle -> running`: the backend accepts the command and returns `202` before reading source content.
- `running -> completed`: the in-process worker finishes source reading and signal detection.
- `running -> failed`: source reading or scan execution fails after acceptance.
- `running -> idle`: the source is deleted before the worker finishes.

Side effects:

- On acceptance, the workflow stores the running scan, started audit event, and zeroed progress metrics.
- On completion, the worker stores scan results without exposing raw source content; polling may apply the completed state after the visible running interval.
- On failure, the worker clears findings and records source-unavailable status.

Rollback path:

- Revert to synchronous `_scan_source` execution inside `start_scan`.
- Remove worker completion persistence and immediate-running scan construction.

## Impact Surface

- Backend scan start handling for prelaunch sources.
- SQLite workflow persistence for in-progress and completed prelaunch scans.
- API contract wording for accepted scan starts.
- Acceptance criteria for user-visible scan-start feedback.

## Primitive Acceptance

- A valid scan command returns `202` with `status = running` before source document reading completes.
- Missing or invalid `sourceId`, not-ready sources, and missing required Google Drive authorization still reject before a running scan is stored.
- A completed worker stores or applies scan status, findings, metrics, evaluation, and audit records for the same `scanId`.
- A stale worker cannot overwrite a newer scan or a cleared workflow.
- No per-scan Google Drive access token is stored in persisted workflow state.
