# Account-Scoped Prelaunch State

## Problem Definition

Prelaunch authentication must isolate user-created Sources, scans, findings, audit events, metrics, and evaluation state. The prior session boundary authenticated requests but reused global SQLite source rows and one global workflow document, so different signed-in accounts could see the same operational state.

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Keep global prelaunch state | Treat all signed-in users as one shared project workspace. | Rejected because it hides account boundaries and leaks user-created source metadata and findings across accounts. |
| Add UI-only filtering | Let the frontend hide rows by account metadata. | Rejected because API responses would still expose cross-account state. |
| Scope SQLite source and workflow rows by session user id | Resolve the first-party session on each request and read/write account-owned source and workflow rows only. | Accepted because it fixes the API boundary without adding tenant, RBAC, or production authorization. |
| Add full organization/tenant model | Introduce workspaces, membership, and roles. | Rejected for this slice because prelaunch needs personal account isolation only. |

## Selected Approach

Authenticated SQLite-backed requests derive an owner id from the first-party session user profile. Source records and workflow documents use `(owner_id, id)` primary keys. The request handler builds owner-scoped source, connection, and workflow services for each protected route. Local development without auth uses an `anonymous` owner scope.

Legacy global SQLite source and workflow rows are migrated to a `legacy_shared` owner scope. They remain in the database for manual recovery but are not returned to authenticated account scopes.

## State Machine

```text
signed_out -> request_rejected
session_active -> owner_scope_resolved
owner_scope_resolved -> source_registered
owner_scope_resolved -> workflow_loaded
source_registered -> account_source_listed
workflow_loaded -> account_findings_listed
owner_scope_resolved -> cross_account_object_requested
cross_account_object_requested -> not_found
session_expired -> request_rejected
```

Guards:

- Protected prelaunch routes require a valid first-party session when `DATASENTINEL_AUTH_REQUIRED=true`.
- The session `userId` is the only owner scope for SQLite-backed prelaunch state.
- A request cannot supply or override `owner_id` through payload fields or headers.

Side effects:

- Source create, update-through-connection-test, and delete mutate only the current owner scope.
- Scan start and completion mutate only the current owner workflow document.
- Finding detail, audit, metrics, and evaluation reads use only the current owner workflow document.

Failure paths:

- Missing or expired session returns authentication required before any scoped store is opened.
- A cross-account source, finding, scan, or review-support request returns not found or the account's empty state.
- Legacy global rows are quarantined under `legacy_shared` rather than attached to an arbitrary account.

Rollback Path

Revert the request-scoped SQLite runtime and restore the previous global `source_records` and `workflow_documents` reads. Existing owner-scoped rows remain in SQLite and can be inspected or migrated manually if a future workspace model replaces personal isolation.

## Impact Surface

- Backend: request routing, SQLite schema migration, source store, workflow store, persistent prelaunch state.
- Frontend: no API shape change; lists and details become account-specific.
- Contracts and docs: clarify first-party session ownership of prelaunch state.
- Deployment: existing global rows are hidden from signed-in account scopes after migration.

## Primitive Acceptance Criteria

- Account A can create and list its own Source.
- Account B cannot list, delete, scan, or connect-test Account A's Source.
- Account A's scan findings appear only in Account A's findings list and detail routes.
- Account B receives an empty account state or not-found response for Account A's finding ids.
- Legacy global SQLite rows are not exposed to authenticated account scopes.
- Local unauthenticated development still has one anonymous scope when auth is disabled.
