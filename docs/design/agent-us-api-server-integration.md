# Agent-us API Server Integration

## Problem

The frontend can render the P0 workflow from local mocks, but `agent-us` needs to act as the project server so the browser can call the documented `/api` contract instead of staying fully disconnected from a backend runtime.

## Research Basis

- Python `http.server` provides `ThreadingHTTPServer`, but the official documentation says it is not recommended for production and only implements basic security checks: https://docs.python.org/3/library/http.server.html.
- Vite `server.proxy` supports proxying development requests that match configured rules without transforming them through Vite: https://vite.dev/config/server-options.
- Caddy `reverse_proxy` forwards matching requests to upstream backends and manages standard forwarded headers: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy.

## Options

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep static-only preview | Lowest operational change | Does not satisfy server-backed `/api` integration | Rejected |
| Add a stdlib Python P0 API behind Caddy | No new dependency, contract-compatible, reversible, enough for demo server integration | Not production-grade and in-memory only | Accepted |
| Add FastAPI or another backend framework | Better production ergonomics | Adds dependency and abstraction before P0 needs it | Rejected |
| Add production database-backed persistence now | Durable state | Expands scope into managed storage, credentials, auth, backup, and rollback | Rejected |
| Add local SQLite persistence after API integration | Restart-safe demo state without a service dependency | Not a production multi-tenant storage model | Accepted by `docs/design/local-sqlite-persistence.md` |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Frontend loaded | `/api/health` and data endpoints respond | Contract envelope is valid | Server-backed demo | Render server data |
| Frontend loaded | `/api` unavailable | Local mocks exist | Mock fallback | Render local fixture workflow |
| Server-backed demo | Full scan requested | Source is P0 `mock_ready` | Scan running | Create scan-start audit event in memory or the configured local SQLite state file |
| Scan running | Completion delay passes and scan is read | Active scan exists | Scan completed | Publish completed scan values and audit event |
| Server-backed demo | Review submitted | Decision, reason, checklist, and target guards pass | Review recorded | Update finding, metrics, and audit event in memory or the configured local SQLite state file |
| Server-backed demo | Invalid command submitted | Guard fails | Previous state | Return `application/problem+json` and keep state unchanged |

## Impact Surface

- Backend source package under `backend/lawdit/`.
- Frontend data provider and API client under `frontend/src/data/`.
- Vite dev-server proxy configuration.
- `agent-us` Caddy routing for `/api/*` to the loopback API server.
- Deployment, TRD, test-case, delivery-workflow, and acceptance documents.

## Rollback Path

1. Stop the Python API service on `agent-us`.
2. Remove the `/api/*` Caddy `reverse_proxy` block and reload Caddy after validation.
3. Revert the frontend API-client wiring to local-only mock state, or leave it in place because it already falls back when `/api` is unavailable.
4. Restore the previous static release symlink if frontend assets need rollback.

## Primitive Acceptance Criteria

- `GET /api/health` returns a contract envelope with `data.ok = true`.
- `GET /api/sources` returns the existing mock-compatible source list.
- `POST /api/scans/full` accepts only a scan-ready controlled source and returns a running scan envelope.
- Rejected scan commands return `application/problem+json` and do not add audit events.
- `POST /api/findings/{findingId}/review` records a review decision, updates the finding status, adds an audit event, and keeps `deletionExecuted = false`.
- The frontend requests `/api` first and continues into local mock workflows only when the backend is unavailable and `VITE_LAWDIT_ENABLE_LOCAL_MOCKS=true`.
- Vite dev mode proxies `/api` to the local backend; Caddy on `agent-us` proxies `/api/*` to the loopback backend.
- No Microsoft Graph, OAuth, tenant integration, production database, queue, AI service, production source connector, or deletion service is introduced.
