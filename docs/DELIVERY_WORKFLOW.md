# Parallel Delivery Workflow

## Goal

Allow frontend, backend, product, and QA workstreams to move in parallel while sharing one tolerant API contract.

## Workstreams

| Workstream | Owns | Must Not Own |
| --- | --- | --- |
| Contract | OpenAPI, mocks, shared state machines, compatibility rules | UI layout or scanner internals |
| Frontend | Screens, components, route behavior, loading and error states | Backend persistence or scanner decisions |
| Backend | API endpoints, scanner pipeline, evaluation, audit persistence | UI styling or frontend routing |
| Product and QA | Acceptance criteria, demo script, test cases, risk review | Hidden implementation details |

## Branch Pattern

- `contract/*` for OpenAPI, mocks, and contract docs.
- `fe/*` for frontend work.
- `be/*` for backend work.
- `docs/*` for non-contract docs.

## First Two Hours

1. Freeze `contracts/openapi.yaml` at version `0.1.0`.
2. Freeze P0 mock payloads in `contracts/mocks/`.
3. Frontend renders admin metrics, findings list, evidence card, review action, audit timeline, evaluation, permissions, and governance settings from mocks.
4. Backend implements `/api/health` and returns mock-compatible scan, findings, governance, and permissions payloads.
5. QA verifies docs, mocks, and OpenAPI use the same field names.

## Integration Gates

### Gate 1: Mock UI Ready

- Frontend can render the P0 demo flow using only mocks.
- Empty, loading, error, and partial data states are visible.
- Unknown enum-like values do not crash rendering.

### Gate 1.5: Remote Preview Ready

- The frontend production build passes before deployment.
- The `agent-us` preview serves the static build through Caddy on port 80.
- Browser-routed paths such as `/dashboard` fall back to the frontend app.
- The preview may proxy `/api/*` to the loopback P0 API server, but must not introduce production source connectors, OAuth flows, tenant integration, database persistence, queue workers, AI services, or deletion services.

### Gate 2: Backend Contract Ready

- Backend exposes every P0 endpoint in the OpenAPI contract.
- Backend returns the response envelope and problem details format.
- Backend accepts `X-Actor-Id` for demo role simulation.
- The first `agent-us` server implementation may keep scan and review mutations in memory while preserving contract-compatible envelopes and no-deletion boundaries.

### Gate 3: First Vertical Slice

- `POST /api/scans/full` creates a scan.
- `GET /api/scans/{scanId}` reports status.
- `GET /api/findings` returns at least one finding.
- `GET /api/findings/{findingId}` returns evidence.
- `POST /api/findings/{findingId}/review` records a decision.
- `GET /api/audit/events` includes the review event.
- `GET /api/users/me/permissions` returns allowed and denied actions.
- `GET /api/findings/{findingId}/review-support` returns checklist, transfer, and escalation support.
- Accepted review decisions include reason, checklist acknowledgement, policy-pack version, permission context, resulting status, and no real deletion in P0.
- `GET /api/audit/events` returns structured audit events with actor, action, object, state transition, evidence references, and no raw sensitive content.

### Gate 4: Evaluation and Demo Confidence

- Admin metrics show scanned files, flagged files, volume, progress, time, review backlog, and high-risk count.
- Evaluation shows precision, recall, F1, reproducibility, throughput, and resource intensity.
- Deletion remains simulated.
- Governance settings show active policy-pack version and source adapter readiness.
- The organizer sample source appears as the default demo source.

## AI Task Brief Template

```markdown
Goal:
Context:
Constraints:
Contract Impact:
Done when:
Validation:
```

## Frontend Agent Rules

- Start from `contracts/mocks/`.
- Keep UI resilient to missing optional fields.
- Treat `meta.partial = true` as renderable with a warning.
- Never display raw sensitive values.
- Do not add endpoint assumptions outside `docs/API_CONTRACT.md`.
- Show denied actions with reasons instead of silently hiding all unavailable controls.

## Backend Agent Rules

- Match `contracts/openapi.yaml` first.
- Keep endpoint responses envelope-wrapped.
- Use `application/problem+json` for errors.
- Make scan and review actions idempotent when `Idempotency-Key` is present.
- Keep real deletion out of P0.
- Return policy-pack version and permission-boundary data when the contract includes it.
- Reject denied, incomplete, stale, or unsupported review decisions before changing finding, audit, metric, source, or evaluation state.

## QA Agent Rules

- Validate English-only developer-facing docs, contracts, mocks, and fixtures; user-facing interface copy may be localized through reviewed frontend dictionaries.
- Compare OpenAPI fields, docs, and mocks.
- Check that state transitions match `docs/API_CONTRACT.md`.
- Confirm that every acceptance change is reflected in `ACCEPTANCE.md`.
