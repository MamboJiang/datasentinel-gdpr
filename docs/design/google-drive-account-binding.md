# Google Drive Account Binding

## Problem Definition

Google Drive sources currently depend on a browser-memory Picker access token. A page refresh drops that token, so imported Drive sources become `authorization_required` even when the same signed-in user intentionally granted Drive access minutes earlier. Users need a personal binding in Account settings that survives refresh, can be changed to another Google account, and can be disconnected without deleting DataSentinel source registrations or Google Drive files.

## Research Basis

- Google OAuth web-server applications can request `access_type=offline` to receive a refresh token and later refresh short-lived access tokens without prompting the user again: https://developers.google.com/identity/protocols/oauth2/web-server
- Google OAuth overview distinguishes browser-only access-token flows from backend flows where the server exchanges an authorization code and stores a refresh token for future access: https://developers.google.com/identity/protocols/oauth2
- Google Drive API scope guidance says applications should request the narrowest scope that covers the needed Drive access: https://developers.google.cn/workspace/drive/api/guides/api-specific-auth?hl=en

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Keep Picker-only per-scan tokens | Avoids refresh-token storage and preserves the prior P0 boundary. | Rejected because refresh predictably loses authorization and blocks the requested durable binding workflow. |
| Store browser access tokens in `localStorage` | Survives refresh without backend changes. | Rejected because access tokens remain short-lived and would expose provider credentials to frontend JavaScript storage. |
| Account-scoped backend Drive binding | Account settings starts Google OAuth consent; backend stores the refresh token in the local account store and injects fresh access tokens only during scans. | Accepted for the prelaunch prototype because it matches the requested durable personal binding while keeping provider tokens off frontend payloads. |
| Workspace-level tenant connector | Central admin connects a tenant-wide Drive inventory. | Rejected for P0 because it expands into production tenant discovery and authorization. |

## Selected Approach

Account settings exposes a Google Drive binding panel:

- `GET /api/integrations/google-drive/binding` returns token-free binding status for the signed-in account.
- `GET /api/integrations/google-drive/bind/start` starts Google OAuth consent with `access_type=offline`, `prompt=consent select_account`, and Drive read scopes.
- `GET /api/integrations/google-drive/bind/callback` validates state, exchanges the code server-side, stores the refresh token in the local account store, and redirects back to the frontend.
- `DELETE /api/integrations/google-drive/binding` removes the local binding and attempts provider token revocation.

Drive source records still store selected item metadata only. The scan request may still include a per-scan Picker access token. If it does not, the backend checks the signed-in user's account binding, refreshes a short-lived access token server-side, and injects it into scan execution. Add Source may also request a short-lived browser-use-only Picker token from the connected binding so Picker opens directly for the bound Google account. Refresh tokens are not returned in API payloads, UI state, source records, workflow documents, findings, metrics, or audit events, and short-lived access tokens must not be persisted.

## State Machine

```text
unbound -> bind_starting
bind_starting -> provider_redirected
provider_redirected -> callback_validating
callback_validating -> bound
bound -> bind_starting
bound -> unbound
```

Events and guards:

- `connect_clicked`: requires a first-party session and configured Google OAuth client credentials.
- `google_callback_received`: requires matching signed transaction state and the same first-party user id.
- `token_exchange_succeeded`: requires an access token, stable Google subject, and refresh token or an existing same-subject refresh token.
- `change_clicked`: follows the same connect path and replaces the previous local binding.
- `disconnect_clicked`: requires a first-party session.

Side effects:

- Store the Drive refresh token server-side under the first-party account id.
- Replace the prior binding when a new Google account is connected.
- Attempt to revoke the prior token when replacing or disconnecting a binding.
- Inject a refreshed access token only into the in-process scan payload.

Failure paths:

- Missing session, missing credentials, provider denial, state mismatch, token exchange failure, missing subject, or missing refresh token returns `driveBinding=failed` or a problem response without creating a binding.
- Refresh failure leaves Drive scans subject to the existing source-unavailable failure path; stale scan-derived findings must not be preserved as if the scan succeeded.
- Revocation failure does not prevent local disconnect, but the UI and payload must not claim upstream revocation succeeded.

Rollback path:

- Disable the Account settings binding panel by removing Google OAuth client credentials or reverting the binding routes.
- Existing `google_drive_selection` source records remain metadata-only and can still be scanned through per-scan Picker authorization.
- Delete rows from the local `google_drive_bindings` table to remove all persisted Drive bindings from a prelaunch SQLite store.

## Impact Surface

- Frontend: Account settings binding panel, Sources status badges, source scan enablement, Dashboard scan source selection.
- Backend: Google Drive binding OAuth routes, local SQLite binding table, scan-start token injection, provider-token revocation attempt.
- Contracts: new binding status envelope and binding routes in `contracts/openapi.yaml` and `docs/API_CONTRACT.md`.
- Security/privacy: refresh tokens are stored server-side in the local prelaunch store, access tokens are refreshed server-side, no token is returned to the browser, and no external source file is deleted or mutated.

## Primitive Acceptance Criteria

- A signed-in user can connect Google Drive from Account settings and the binding status shows `connected = true` without exposing access or refresh tokens.
- Refreshing the page after registering a Google Drive source keeps that source scan-ready when the account binding is connected.
- A Google Drive scan without a per-scan Picker token uses the account binding server-side and does not include provider tokens in public payloads.
- A user can change the Drive binding; the new binding replaces the old local binding and old-token revocation is attempted.
- A user can disconnect the Drive binding; Drive source registrations remain, external Drive files are untouched, and future scans need a new binding or per-scan Picker token.
- Missing or invalid binding state does not fall back to stale mock findings.
