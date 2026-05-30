# Owner Routing and Assignment

## Problem Definition

After context and risk judgment, DataSentinel must route each review-required finding to an accountable owner or escalation path. The stage must preserve continuity from evidence, context, risk, and policy guidance while making accountability visible before human review begins.

This P0 slice is deterministic and fixture-backed. It extends the existing scan workflow after `judging_context_risk` and before scan completion. It does not add production identity, Microsoft Graph, OAuth, notification, deletion, or tenant integrations.

## Scope

In scope:

- A scan-level optional `ownerAssignment` summary on the existing scan payload.
- A visible `assigning_owner` pipeline stage after `judging_context_risk`.
- Deterministic routing counts for direct owners, Master of Data fallback, and escalation routes.
- Policy-pack version, organization-model version, owner-resolution strategy, and assignment-rule fingerprint.
- Dashboard visibility for owner-routing status and unowned-finding count.
- Audit-visible owner-assignment completion when review-required findings become assigned.
- Evaluation linkage through an owner-assignment rules hash with zero model calls and zero estimated paid-service cost.

Out of scope:

- Production directory lookup, Microsoft Graph, OAuth, tenant sync, email, Teams, Slack, or ticket creation.
- Automatic deletion, quarantine, source mutation, or remote permission changes.
- Legal advice, legal conclusions, or claims of GDPR compliance.
- Public endpoints for internal owner-resolution stages.
- Hard-coded legal rules inside scanner logic.

## Research Basis

- GDPR Article 5(2) establishes accountability, so review work must have an attributable owner rather than an anonymous system queue.
- GDPR Article 24 requires controller responsibility measures that account for nature, scope, context, purpose, risk, and implementation cost, which supports a configurable organization model instead of hard-coded owners.
- GDPR Article 32 frames controls around state of the art, implementation cost, and risk, which supports a deterministic, low-cost P0 stage before any production identity integration.
- GDPR Article 35 and EDPB DPIA guidance treat high-risk processing as a structured assessment topic; DataSentinel routes high-risk findings for human review instead of issuing legal conclusions.

References:

- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- EDPB DPIA high-risk processing guidance page: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/data-protection-impact-assessments-high-risk-processing_en

## Atlas-Derived Continuity Requirements

The requirements below are derived from the repository Atlas reference in `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md`, `docs/design/deterministic-signal-detection.md`, `docs/design/context-risk-judgment.md`, and the governance contract.

| ID | Requirement |
| --- | --- |
| OWNROUTE-REQ-001 | Owner routing must run only after deterministic signal detection and context/risk judgment exist; it cannot invent review work without detector evidence. |
| OWNROUTE-REQ-002 | Owner routing must use source metadata, source Master of Data fallback, organization model, and policy-pack guidance rather than raw file bodies. |
| OWNROUTE-REQ-003 | Every review-required finding must become direct-owner assigned, Master of Data assigned, or escalation routed; findings must never be silently unowned. |
| OWNROUTE-REQ-004 | Assignment output must explain the routing strategy without making a legal conclusion or executing deletion. |
| OWNROUTE-REQ-005 | Policy-pack version, organization-model version, and assignment-rule fingerprint must be preserved for audit and reproducibility. |
| OWNROUTE-REQ-006 | Missing owner metadata must degrade to fallback or escalation, not raw-content inspection or hidden failure. |
| OWNROUTE-REQ-007 | The stage must keep model calls and estimated paid-service cost at zero in P0. |
| OWNROUTE-REQ-008 | The stage must preserve continuity for review support, permission boundaries, audit events, metrics, and evaluation. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Integrate a production directory or Microsoft Graph lookup now | Closer to enterprise deployment | Adds credentials, tenant permissions, privacy review, and operational cost before P0 needs it | Rejected |
| Use an LLM to infer owners from file content | Flexible for unknown corpora | Requires raw-content handling, paid calls, and reproducibility controls | Rejected |
| Hard-code owners per finding fixture | Very fast | Hides organization-model behavior and weakens rollback | Rejected |
| Use deterministic source, organization-model, and policy-pack routing | Free, testable, reproducible, and compatible with current mocks | Does not resolve arbitrary real users | Accepted for P0 |
| Add a public owner-resolution endpoint | Debuggable stage boundary | Expands public contract and couples UI to an internal workflow | Rejected |
| Add optional `ownerAssignment` on existing scan payload | Observable and tolerant-client compatible | Requires docs, schema, mock, UI, and tests to stay synchronized | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Judging context risk | Context/risk completed | Review-required findings are counted | Assigning owner | Build owner-routing input from source, context/risk, policy pack, and organization model |
| Assigning owner | Direct owner available | Owner signal has enough confidence | Assigned to direct owner | Count direct-owner assignment |
| Assigning owner | Direct owner unavailable | Source Master of Data is configured | Assigned to Master of Data fallback | Count fallback assignment |
| Assigning owner | Policy escalation is required | Escalation path exists | Escalation routed | Count escalation assignment |
| Assigning owner | Owner unavailable | Escalation path exists | Escalation routed | Count escalation assignment |
| Assigning owner | Owner and escalation unavailable | No accountable path exists | Assignment failed or partial | Preserve prior scan state and expose warning or problem details |
| Assigning owner | Assignment completed | `unownedFindings = 0` | Scan completed | Publish assignment summary, audit event, metrics, and evaluation hash |
| Assigned | Reviewer transfers task | Transfer option is allowed | Transfer pending | Review command records reason and audit event |
| Transfer pending | Target accepts | Target can review scope | Assigned | Owner changes with audit history preserved |
| Transfer pending | Target rejects | Previous owner remains accountable | Assigned | Rejection is audit-visible in backend implementations |

## Public Contract Strategy

The public contract does not gain a new endpoint. The scan payload may include optional `ownerAssignment` data:

- `status`
- `policyPackVersion`
- `organizationModelVersion`
- `ownerResolutionStrategy`
- `assignmentRulesFingerprint`
- `humanReviewRequiredFindings`
- `assignedFindings`
- `directOwnerAssignments`
- `masterOfDataAssignments`
- `escalationAssignments`
- `unownedFindings`
- `transferOptionCount`
- `escalationOptionCount`
- `sourceOwnerAvailable`
- `warnings`

Admin metrics may include optional owner-routing counters. Evaluation may include `ownerAssignmentRulesHash`. Clients must ignore unknown fields and render missing optional values neutrally.

## Privacy and Security Boundaries

- The stage consumes source metadata, context/risk counts, policy-pack metadata, and organization-model metadata.
- Public payloads must not expose raw extracted text, full file content, page images, unredacted personal data, salts, secrets, directory tokens, or hidden permission data.
- Owner routing is operational accountability guidance, not legal advice.
- Deletion remains represented only as a human-review decision candidate; no source file can be changed by this stage.
- Missing owner data must produce fallback, escalation, warning, or problem details rather than hidden auto-assignment.
- Permission boundaries remain explicit through the existing permission and review-support surfaces.

## Economic Affordability

P0 uses deterministic fixture-backed routing with zero model calls, zero estimated paid-service cost, and no new runtime dependency. A future production path should preserve this cost order:

1. Deterministic metadata and organization-model mapping.
2. Existing enterprise directory metadata only after tenant permissions and security review are approved.
3. Notification or ticket integrations only after audit semantics are stable.
4. AI-assisted owner suggestion only for low-confidence routing, with redaction, approval, and evaluation controls.

## Rollback Path

Remove the optional `ownerAssignment` field, the `assigning_owner` pipeline stage, optional owner metrics, Dashboard owner-routing panel rows, and `ownerAssignmentRulesHash`. Existing endpoints and required fields remain unchanged, so rollback does not require a contract version bump.

## Primitive Acceptance Criteria

- A completed full scan exposes an `assigning_owner` pipeline stage after `judging_context_risk`.
- A running scan shows owner assignment as pending until context/risk judgment completes.
- The completed scan exposes an `ownerAssignment` summary with policy-pack version, organization-model version, strategy, rules fingerprint, routed counts, and `unownedFindings = 0`.
- Owner routing consumes context/risk human-review counts and source governance metadata without raw source content.
- Dashboard shows owner-routing status, assigned findings, fallback assignments, escalation assignments, and unowned count without presenting legal conclusions.
- Owner routing creates an audit-visible event when review-required findings are routed.
- Evaluation preserves an owner-assignment rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, context/risk, owner-assignment, or audit state changes.
- Behavior tests cover running, completed, fallback, escalation, no-unowned, audit, no-raw-content, cost boundary, and not-ready-source paths.
