# Adaptive Governance and Review Control Design

## Problem Definition

DataSentinel must not depend on one fixed snapshot of legal rules, organization charts, or ownership structures. Enterprises face policy changes, reorganizations, task transfers, temporary reviewer coverage, legal exceptions, and source migration. Reviewers also need a friendly workflow that makes responsibilities, choices, evidence, and permission boundaries obvious.

## Design Requirements

- Keep system structure law-agnostic and policy-pack driven.
- Give human reviewers clear evidence, action choices, guidance, and escalation paths.
- Support organization changes, ownership transfer, task delegation, policy version changes, and regulatory updates.
- Make user permissions and action boundaries visible before the user acts.
- Use organizer sample files as the baseline demo source and evaluation reference.

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Hard-code GDPR rules into scanner logic | Fast demo | Brittle when policies or jurisdictions change | Rejected |
| Store rules as editable policy packs | Adaptable and auditable | Requires versioning discipline | Accepted |
| Put review instructions only in UI text | Easy for frontend | Backend cannot validate actions consistently | Rejected |
| Expose reviewer support through API | Consistent across UI, audit, and backend validation | Adds contract surface | Accepted |
| Hide permission failures until submit | Simple backend | Poor user control and trust | Rejected |
| Return available and denied actions upfront | Clear user boundaries | Requires role-context payload | Accepted |

## Decision

Add an adaptive governance layer to the contract:

- `GovernanceConfig` describes active policy pack, organization model, review queues, source adapters, and change controls.
- `PolicyPack` stores versioned, law-agnostic rules such as retention logic, evidence requirements, review decisions, escalation rules, and jurisdiction tags.
- `PermissionBoundary` tells users what they can do, what they cannot do, and why.
- `ReviewSupport` gives reviewer-friendly action guidance, checklists, required reasons, transfer options, and escalation options.
- Organizer samples from `a-klumpp/GDPR-data-samples` become the default contract-backed demo source.

## Governance State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Draft policy | Admin edits policy | Editor has governance permission | Validating | Validate rule shape |
| Validating | Validation passes | Required fields exist | Pending activation | Create audit preview |
| Validating | Validation fails | Blocking issue exists | Draft policy | Return problem details |
| Pending activation | Admin activates | Change window accepted | Active policy | Record policy version |
| Active policy | New policy activated | Replacement is valid | Superseded policy | Preserve old audit context |
| Active policy | Rollback requested | Previous active policy exists | Rolled back | Restore previous version |

## Review Task State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Assigned | Reviewer opens task | Reviewer has read permission | In review | Record task viewed |
| In review | Reviewer delegates | Target can accept task | Transfer pending | Notify target owner |
| Transfer pending | Target accepts | Target has review permission | Assigned | Reassign task |
| Transfer pending | Target rejects | Original owner still valid | Assigned | Record rejection reason |
| In review | Reviewer escalates | Escalation path exists | Escalated | Notify DPO or Legal |
| In review | Reviewer decides | Decision has required reason | Reviewed | Create audit event |
| Reviewed | Policy changes | Decision affected by new rule | Reopen candidate | Queue for admin review |

## Permission Boundary State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Unknown boundary | User context loaded | Actor identified | Boundary calculated | Return allowed and denied actions |
| Boundary calculated | User requests allowed action | Action is allowed | Action accepted | Record actor and reason |
| Boundary calculated | User requests denied action | Action is denied | Action rejected | Return problem details with reason |
| Boundary calculated | Role changes | Admin updates role or org | Boundary stale | Recalculate boundary |

## Impact Surface

- Frontend must show available actions, denied actions, and reasons instead of hiding permission uncertainty.
- Backend must calculate review support from finding state, active policy pack, org model, and actor role.
- Audit events must preserve policy version and actor context.
- Evaluation can run against organizer sample families and policy-pack versions.
- Existing scan and finding endpoints remain compatible; new governance fields are optional.

## Rollback Path

If the governance layer is too large for P0:

1. Keep `GET /api/governance/config` and `GET /api/users/me/permissions`.
2. Render static policy-pack mock values from `contracts/mocks/governanceConfig.json`.
3. Keep review support inside `findingDetail.json` until the backend endpoint exists.
4. Defer policy activation endpoints and keep policy changes as documentation-only.

## Primitive Acceptance Criteria

- The UI can show which actions the current user may take and why other actions are unavailable.
- A reviewer can see guidance, required evidence, reason requirements, escalation choices, and transfer choices before deciding.
- A finding can reference the policy pack version used for classification and review.
- An admin can inspect active governance settings without changing code.
- A policy version change can be represented without changing scanner code.
- A task transfer can be represented without changing finding schema.
- Organizer sample files are represented as the default sample source.
- No API response claims a legal conclusion; it exposes configurable policy guidance and human review support.
