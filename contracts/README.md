# Contracts

This folder contains the frontend-backend delivery contract.

- `openapi.yaml` is the machine-readable API source of truth.
- `schemas/` keeps schema files split below the repository file-size guardrail.
- `mocks/` contains contract fixtures for frontend work before backend endpoints exist.

Contract version: `0.1.0`.

Compatibility rule: additive optional response fields are allowed; breaking changes require a version bump and updates to `docs/API_CONTRACT.md`.
