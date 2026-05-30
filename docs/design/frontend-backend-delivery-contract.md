# Frontend-Backend Delivery Contract Design

## Problem Definition

The team plans to build frontend and backend in parallel. Without a shared contract, frontend agents may invent fields while backend agents return incompatible structures, causing late integration failures.

The project needs a broad, tolerant contract that supports early UI work, backend scanner iteration, and demo stability without locking the team into production infrastructure.

## Requirements

- Frontend can build the full P0 demo path from mocks.
- Backend can implement endpoints incrementally.
- Contract changes are visible and reviewable.
- Unknown future fields do not break clients.
- Unknown enum-like values degrade gracefully.
- Errors are machine-readable.
- No P0 endpoint performs real deletion.

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Ad hoc JSON examples | Fastest to write | High mismatch risk and weak validation | Rejected |
| Backend-first implementation | Backend can shape data naturally | Frontend blocks on backend readiness | Rejected |
| GraphQL-first | Flexible client queries | Adds schema and resolver complexity not needed for P0 | Deferred |
| OpenAPI-first plus mocks | Stable enough for agents and tooling, simple REST mental model | Requires contract discipline | Accepted |

## Decision

Use `OpenAPI-first + mock-first + vertical-slice-first`.

The contract is intentionally tolerant:

- Objects allow additive optional fields.
- Response envelopes carry metadata, warnings, and trace IDs.
- Enum-like fields are documented as open strings.
- Errors use RFC 9457 problem details.
- Mocks are part of the contract fixtures.

## Research Basis

- OpenAPI 3.1 is selected because it provides a standard HTTP API description format and uses JSON Schema 2020-12 semantics for schema objects: https://spec.openapis.org/oas/v3.1.0.html
- JSON Schema object semantics support optional fields and additional properties by default, which matches the tolerance goal: https://json-schema.org/understanding-json-schema/reference/object
- RFC 9457 problem details are selected for structured error responses: https://www.rfc-editor.org/rfc/rfc9457.html

## Contract State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Draft | Contract written | P0 endpoints listed | Mocked | Create mock payloads |
| Mocked | Mocks reviewed | Field names match docs | Frozen | Set contract version |
| Frozen | Frontend starts | No breaking field change | Frontend in progress | UI renders mocks |
| Frozen | Backend starts | No breaking field change | Backend in progress | API implements envelopes |
| Backend in progress | Endpoint matches mock | P0 slice available | Integrated | Frontend calls real endpoint |
| Integrated | Additive field needed | Existing clients tolerate it | Frozen | Update docs and mocks |
| Integrated | Breaking change needed | Team approves version bump | Draft | Create new contract version |

## Domain State Machines

### Scan

`queued -> running -> completed`

Failure paths:

- `queued -> failed`
- `running -> failed`
- `running -> cancelled`

Retry path:

- `failed -> queued`

### Finding Review

`open -> assigned -> under_review -> reviewed -> closed`

Terminal variants:

- `delete_candidate`
- `retained`
- `false_positive`
- `escalated`

Guard: every terminal review decision requires a human actor and reason.

## Impact Surface

- Frontend routes and components consume `contracts/mocks/` and later `/api`.
- Backend API controllers must match `contracts/openapi.yaml`.
- QA validates docs, mocks, and OpenAPI consistency.
- PR reviews must flag contract drift.
- Acceptance criteria now include contract readiness and mock readiness.

No production storage, authentication, Microsoft Graph, or deletion path is introduced by this design.

## Rollback Path

If the contract proves too broad or unstable:

1. Keep mock fixtures as the frontend fallback.
2. Freeze only the first vertical slice endpoints.
3. Move uncertain fields into `extensions`.
4. Mark unstable endpoints as deferred in `docs/API_CONTRACT.md`.
5. Version the next contract as `0.2.0` only after team approval.

## Primitive Acceptance Criteria

- A frontend agent can render the P0 demo flow using only mock JSON.
- A backend agent can implement P0 endpoints without asking for field names.
- A client that receives an unknown optional field still renders the known fields.
- A client that receives an unknown enum-like value displays a neutral fallback.
- A failed request returns `application/problem+json` with a trace ID.
- A review decision cannot be represented without a human actor and reason.
- A deletion action is represented only as a simulated deletion candidate in P0.
