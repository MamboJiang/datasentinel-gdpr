# Acceptance Criteria

## Repository Initialization

The initialization is complete when:

- The GitHub repository is public.
- The local repository has a clean `main` branch after the initial commit is pushed.
- The repository contains English-language planning documents for BRD, MRD, PRD, TRD, DesignSpec, TestCase, and acceptance criteria.
- The repository does not contain implementation code, runtime dependencies, secrets, generated build artifacts, or copied source data from the challenge PDF.
- The project README clearly states the project thesis, current scope, and non-goals.
- The listed teammates are invited as GitHub collaborators.

## Project Readiness

The project is ready for implementation only when:

- The team approves the initial requirements and acceptance criteria.
- The first implementation task has a narrow, testable scope.
- Any new workflow, external API integration, permission model, or deletion mechanism has a design note with state transitions, failure paths, rollback paths, and primitive acceptance criteria.

## Parallel Delivery Contract Readiness

Frontend-backend parallel development may start when:

- `docs/API_CONTRACT.md` defines the P0 endpoints, envelope, tolerance rules, error format, and state machines.
- `contracts/openapi.yaml` and `contracts/schemas/` define the machine-readable contract.
- `contracts/mocks/` contains payloads for sources, scan status, findings list, finding detail, audit events, admin metrics, and latest evaluation.
- `docs/DELIVERY_WORKFLOW.md` defines frontend, backend, contract, and QA responsibilities.
- `AGENTS.md` and `.github/copilot-instructions.md` tell teammate AI tools how to follow the contract.
- No frontend or backend implementation code is introduced before the first scoped implementation task.
- `docs/GOVERNANCE_CONFIG.md` defines policy packs, organization model, permission boundaries, review support, and enterprise change scenarios.
- `docs/GDPR_SAMPLE_REFERENCES.md` records how the organizer sample repository is used without vendoring PDFs.

## P0 Product Acceptance

The first implementation milestone is accepted when:

- A full scan can be started on a controlled sample source.
- Admin metrics show scanned files, flagged files, scanned volume, progress, scan time, review backlog, high-risk count, and retention-overdue count.
- A responsible user can list assigned findings.
- A finding detail view shows redacted evidence, signals, risk explanation, owner assignment, retention status, and audit timeline.
- A human reviewer can record delete candidate, keep with reason, false positive, reassign, or escalate decisions.
- Every review decision creates an audit event with actor, timestamp, reason, and resulting status.
- A delta scan can represent changed-file-only processing.
- Evaluation metrics show precision, recall, F1, reproducibility, throughput, and resource intensity.
- Deletion remains simulated.

## Adaptive Governance Acceptance

The design points are accepted when:

- Legal or policy details can be represented as a versioned policy pack instead of hard-coded scanner logic.
- A reviewer can see plain-language support, required checklist items, available decisions, transfer options, escalation options, and required reason fields.
- A user can see allowed actions, denied actions, denial reasons, and visible scopes before attempting an action.
- Ownership transfer, personnel change, organization model change, policy version change, and regulatory update scenarios are represented in docs and contract mocks.
- Audit and evaluation payloads can preserve the policy-pack version used for a finding or decision.
- The organizer sample repository is represented as a default demo source with sample families.
