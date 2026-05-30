# DataSentinel AI Agent Instructions

## Mission

Help the team build DataSentinel as an English-only, contract-first, human-accountable GDPR data discovery prototype.

The product is not a generic PII scanner. It is a measurable workflow that discovers GDPR-relevant data, explains evidence, routes findings to accountable owners, supports human review, records audit events, and reports evaluation metrics.

## Required Start Pattern

Before changing files, write a short task brief in the working thread:

- Goal
- Context
- Constraints
- Done when
- Impact surface

If the change affects requirements, behavior, API shape, states, roles, permissions, evaluation metrics, or acceptance criteria, update the relevant document in `docs/` and `ACCEPTANCE.md`.

## Non-Negotiables

- Keep all repository content in English.
- Do not implement automatic deletion.
- Do not claim full GDPR compliance or provide legal advice.
- Do not add production Microsoft Graph, OAuth, tenant, or deletion integrations in P0.
- Do not add dependencies, frameworks, or abstractions before a task explicitly needs them.
- Do not invent API fields or endpoints outside `docs/API_CONTRACT.md` and `contracts/openapi.yaml`.
- Do not break existing mock payloads unless the contract version changes and affected docs are updated.
- Do not hard-code one legal snapshot into scanner or review structure; use policy-pack concepts from `docs/GOVERNANCE_CONFIG.md`.
- Do not hide user permission boundaries. Expose allowed and denied actions when the contract provides them.

## Parallel Delivery Contract

Frontend and backend work in parallel through the shared contract:

- Contract source of truth: `contracts/openapi.yaml`.
- Human-readable contract: `docs/API_CONTRACT.md`.
- Mock payloads: `contracts/mocks/`.
- Product context: `docs/PROJECT_CONTEXT.md`.
- Delivery workflow: `docs/DELIVERY_WORKFLOW.md`.
- Governance model: `docs/GOVERNANCE_CONFIG.md`.
- Organizer samples: `docs/GDPR_SAMPLE_REFERENCES.md`.

Frontend agents may build UI against mock payloads before backend endpoints exist. Backend agents must return the same envelope shape and field names as the mocks.

## Compatibility Rules

- Clients must ignore unknown response fields.
- Servers may add optional fields without a breaking change.
- Required fields must remain stable inside a contract version.
- Unknown enum-like string values must render as `unknown` or a neutral UI state.
- Empty arrays are valid.
- Optional objects may be `null` or omitted when the backend cannot know the value yet.
- Error responses must use `application/problem+json` as documented.

## Branch Ownership

- `contract/*`: API contract, mocks, shared docs.
- `fe/*`: frontend implementation.
- `be/*`: backend implementation.
- `docs/*`: non-contract documentation.

Keep implementation branches scoped. Do not let frontend and backend agents edit the same files unless the task explicitly requires contract coordination.

## Review Checklist

Before finishing a task, verify:

- The change stays within the requested scope.
- The contract still matches mocks and docs.
- State transitions remain valid.
- Sensitive values remain redacted in examples and UI-facing payloads.
- Tests or validation commands were run for the touched surface.
- No dead code, commented-out code, or unowned TODOs were added.
