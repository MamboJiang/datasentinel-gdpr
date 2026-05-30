# Technical Requirements Document

## Current Technical Scope

This repository is initialized for documentation and collaboration. No runtime architecture, framework, dependency, database, or external API integration is approved yet.

## Technical Principles

- Keep implementation changes small, testable, and reversible.
- Prefer explicit boundaries between source connectors, classification, review workflow, audit logging, and presentation.
- Inject external collaborators into core logic instead of constructing them inside core modules.
- Keep side effects at boundary layers.
- Use behavior tests for user-observable contracts.

## Future Boundary Candidates

These are not approved implementation modules yet. They are candidate boundaries to evaluate before coding:

- Source connector boundary.
- Document extraction boundary.
- Finding classification boundary.
- Risk scoring boundary.
- Owner resolution boundary.
- Human review workflow boundary.
- Audit event boundary.
- Delta scan boundary.

## External Research Required Before Implementation

Official or authoritative documentation must be reviewed before integrating:

- Microsoft Graph or any file-source API.
- GDPR deletion, retention, or audit-related workflow assumptions.
- Any AI, OCR, document parsing, or classification dependency.
- Any storage, authentication, authorization, or deployment platform.

## Technical Done When

The first implementation task has:

- A narrow acceptance criterion.
- A documented impact surface.
- A state machine if it introduces workflow, permissions, asynchronous work, or external protocols.
- Targeted validation commands.

