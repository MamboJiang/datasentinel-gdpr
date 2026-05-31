# Governance Configuration

## Purpose

Governance configuration lets DataSentinel adapt to policy changes, organization changes, task transfers, source changes, and reviewer permissions without hard-coding one legal snapshot into the system.

Related contract files:

- `contracts/schemas/governance.yaml`
- `contracts/schemas/workspace.yaml`
- `contracts/mocks/governanceConfig.json`
- `contracts/mocks/permissionBoundary.json`
- `contracts/mocks/reviewDecision.json`
- `contracts/mocks/reviewSupport.json`
- `contracts/mocks/workspaceDirectory.json`
- `contracts/mocks/workspaceAdmin.json`

## Principles

- Law-specific details live in versioned policy packs, not scanner structure.
- Review actions are human decisions with guidance, not automatic legal conclusions.
- Admins can inspect active configuration, policy version, queues, roles, and source adapters.
- Users can see their permission boundary before acting.
- Audit events should preserve the policy version and actor context that existed when a decision was made.

## Configuration Objects

| Object | Purpose |
| --- | --- |
| `PolicyPack` | Versioned policy guidance, retention rules, context/risk guidance, evidence requirements, escalation paths, and allowed review decisions. |
| `OrganizationModel` | Org units, owner resolution strategy, Master of Data fallback, delegation rules, and delegation targets. |
| `PermissionBoundary` | Allowed actions, denied actions, denial reasons, visible data scopes, boundary fingerprint, and evaluation timestamp for the current actor. |
| `ReviewSupport` | Reviewer guidance, checklist, available decisions, required reason fields, transfer options, and escalation options. |
| `ReviewDecision` | Human decision record with reason, checklist acknowledgement, target or retention context, resulting status, audit event, and no-real-deletion boundary. |
| `SourceAdapterConfig` | Demo source, local source, direct HTTPS file link, Google Drive selected source, mock SharePoint, and future connector readiness. |
| `Workspace` | Accountable operational boundary for members, groups, invitations, sources, findings, audit, evaluation, and admin charts. |
| `WorkspaceGroup` | Workspace-scoped role-like group carrying explicit permissions such as admin management, review, stewardship, or audit read access. |
| `WorkspaceInvitation` | Pending, accepted, expired, or revoked invite link that turns a signed-in account into a Workspace member only after acceptance. |

## Policy Pack Shape

```json
{
  "policyPackId": "policy_gdpr_demo",
  "version": "2026.05-demo",
  "status": "active",
  "jurisdictionTags": ["EU", "GDPR"],
  "effectiveFrom": "2026-05-30",
  "retentionRules": [
    {
      "ruleId": "retention_default_3y",
      "documentCategory": "supplier_onboarding",
      "reviewAfterDays": 1095,
      "guidance": "Review whether a business purpose still exists."
    }
  ],
  "riskGuidance": [
    {
      "guidanceId": "risk_supplier_financial_identifiers",
      "contextCategory": "supplier_onboarding",
      "signalTypes": ["iban_like", "billing_address", "signature"],
      "riskLevel": "high",
      "scoreFloor": 80,
      "reviewReason": "Financial and signature identifiers require accountable human review."
    }
  ],
  "reviewDecisions": ["delete_candidate", "keep_with_reason", "correct_false_positive", "reassign_owner", "escalate"]
}
```

## Admin Operations

P0 exposes configuration for inspection and mock-driven UI. Production editing is deferred.

- View active governance configuration.
- View active policy pack and version.
- View org units and owner fallback model.
- View permission boundaries.
- Preview policy or org changes before activation.
- View Workspace members, groups, pending invite links, and group-derived permission boundaries.
- Change Workspace profile settings when `manage_workspace_settings` is present.
- Create, rename, re-permission, and delete Workspace groups when `manage_workspace_groups` is present.
- Generate invite links into a Workspace with explicit group assignment.

## Workspace Groups

Workspace groups are the P0 role carrier. Account sign-in does not grant Workspace access by itself.

Workspace admins can add custom groups from the exposed permission catalog. Custom group IDs are opaque and remain stable across rename operations. Deleting a non-admin group removes the group reference from active members and pending invite links; pending links with no remaining groups become revoked. The `workspace_admin` group remains protected so it cannot be deleted or stripped of `view_workspace_admin`, `manage_workspace_settings`, plus `manage_workspace_groups`.

| Group | Purpose | Representative permissions |
| --- | --- | --- |
| `workspace_admin` | Manage the Workspace control plane. | `view_workspace_admin`, `manage_workspace_settings`, `invite_workspace_members`, `manage_workspace_members`, `manage_workspace_groups`, `view_workspace_metrics`, `view_workspace_audit`, `view_governance`, `view_review_support` |
| `privacy_reviewer` | Review assigned findings with visible support. | `view_assigned_findings`, `review_findings`, `view_review_support` |
| `data_steward` | Own source or department stewardship decisions. | `view_owned_sources`, `view_assigned_findings`, `review_findings` |
| `auditor` | Inspect evidence without mutating workflow state. | `view_workspace_audit`, `view_workspace_metrics`, `view_governance` |

Real deletion stays denied as `execute_real_deletion` for every group in P0.

## Review Support Rules

P0 review support is derived from:

- The assembled finding and redacted evidence card.
- Active `PolicyPack.reviewDecisions`, `evidenceRequirements`, and `escalationPaths`.
- `OrganizationModel.delegationTargets` for controlled transfer choices.
- The actor's visible `PermissionBoundary`.

The default reviewer can see `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate` when those actions are allowed. Every decision requires a reason and required checklist acknowledgement. `keep_with_reason` also requires a retention review date. Real deletion remains represented only as denied `execute_real_deletion`; no P0 governance setting enables source-file deletion.

## Enterprise Change Scenarios

| Scenario | Contract Support |
| --- | --- |
| Personnel reorganization | `OrganizationModel` and owner fallback can change while findings keep audit history. |
| Task transfer | `ReviewSupport.transferOptions` and review decision `reassign_owner`. |
| Regulatory change | New `PolicyPack.version` with preserved historical policy context. |
| Department rename | Org unit IDs stay stable while display names change. |
| Temporary reviewer absence | Delegation rules and transfer options route work without changing findings. |
| Legal hold or exception | Review support can require escalation or keep-with-reason. |
