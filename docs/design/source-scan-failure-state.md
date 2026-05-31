# Source Scan Failure State

## Problem

Google Drive sources store selected item metadata but not access tokens. When a saved Drive source is scanned after its short-lived Picker token is missing or expired and no account-level Drive binding is connected, the server rejects the command. The frontend must not treat that business rejection as a server outage and must not fall back to local mock scanning, because that can surface stale demo findings as if they came from the selected source.

## Options

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep rejecting without state changes | Preserves the previous command contract | Stale findings remain visible after a failed source read | Rejected |
| Frontend-only disable Drive scans without runtime token or account binding | Prevents common accidental retries | Direct API calls and expired-token or refresh-failure paths can still leave stale findings | Partial |
| Add explicit failed scan state and suppress local mock fallback for API rejections | Clears stale scan-derived findings and keeps server/business errors distinct from outages | Requires a small frontend data contract and backend state transition | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effects |
| --- | --- | --- | --- | --- |
| Source selected | Register Google Drive source | Picker returned selected items | Authorization required | Store selected item metadata only; do not store tokens. |
| Authorization required | Picker token exists in current browser session | Source adapter is connected | Scan start allowed | Send token in the one scan request. |
| Authorization required | Account Drive binding is connected | Source adapter is connected | Scan start allowed | Backend refreshes a short-lived access token server-side for the scan. |
| Authorization required | Scan requested without runtime token or connected binding | Source is Google Drive | Failed scan | Reject with problem details, clear scan-derived findings, keep source files untouched. |
| Connected source | Source read fails | Token expired, refresh failed, source unreadable, or external read fails | Failed scan | Reject with problem details, clear scan-derived findings, record zero metrics and warning. |
| Any server command | API returns `application/problem+json` | Response reached the project server | No local fallback | Show the rejection reason and keep server connection status unchanged. |
| Any server command | Network/server unavailable | Request cannot reach the project server | Local fallback only when enabled | Mark server disconnected and use local mock fallback only for development/unavailable-server mode. |

## Impact Surface

- Frontend data provider command error handling.
- Sources and Dashboard scan button readiness, including account-level Drive binding state.
- Backend prelaunch scan state after source-read failures.
- SQLite workflow persistence for failed scan state.
- Acceptance and console contract wording.

## Rollback Path

Revert the API request error class, runtime-authorized source readiness helper, account binding readiness input, failed-scan state transition, and this design note. Existing server scan and source registration APIs remain compatible with per-scan Picker authorization.

## Primitive Acceptance Criteria

- A Google Drive source with no current Picker token and no connected account binding cannot be started from the Sources or Dashboard scan buttons.
- A server 409/422/403 command rejection is shown as a command rejection, not treated as a project-server outage.
- A failed Google Drive source read clears visible scan-derived findings instead of preserving old demo or prior-source findings.
- Failed source reads do not delete external files, store provider tokens, expose raw source content, or claim legal conclusions.
