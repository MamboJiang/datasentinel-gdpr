# Governance Configuration

## Purpose

Governance configuration lets DataSentinel adapt to policy changes, organization changes, task transfers, source changes, and reviewer permissions without hard-coding one legal snapshot into the system.

Related contract files:

- `contracts/schemas/governance.yaml`
- `contracts/mocks/governanceConfig.json`
- `contracts/mocks/permissionBoundary.json`
- `contracts/mocks/reviewSupport.json`

## Principles

- Law-specific details live in versioned policy packs, not scanner structure.
- Review actions are human decisions with guidance, not automatic legal conclusions.
- Admins can inspect active configuration, policy version, queues, roles, and source adapters.
- Users can see their permission boundary before acting.
- Audit events should preserve the policy version and actor context that existed when a decision was made.

## Configuration Objects

| Object | Purpose |
| --- | --- |
| `PolicyPack` | Versioned policy guidance, retention rules, evidence requirements, escalation paths, and allowed review decisions. |
| `OrganizationModel` | Org units, owner resolution strategy, Master of Data fallback, and delegation rules. |
| `PermissionBoundary` | Allowed actions, denied actions, denial reasons, and visible data scopes for the current actor. |
| `ReviewSupport` | Reviewer guidance, checklist, available decisions, required reason fields, transfer options, and escalation options. |
| `SourceAdapterConfig` | Demo source, local source, mock SharePoint, and future connector readiness. |

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

## Enterprise Change Scenarios

| Scenario | Contract Support |
| --- | --- |
| Personnel reorganization | `OrganizationModel` and owner fallback can change while findings keep audit history. |
| Task transfer | `ReviewSupport.transferOptions` and review decision `reassign_owner`. |
| Regulatory change | New `PolicyPack.version` with preserved historical policy context. |
| Department rename | Org unit IDs stay stable while display names change. |
| Temporary reviewer absence | Delegation rules and transfer options route work without changing findings. |
| Legal hold or exception | Review support can require escalation or keep-with-reason. |
