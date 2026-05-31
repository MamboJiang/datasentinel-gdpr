# Workspace Admin Permission System

## Problem Definition

DataSentinel has prelaunch account sign-in, but an account is not the same thing as a workspace identity. The product needs a workspace-scoped administration surface so accountable administrators can invite people, assign user groups, inspect permission boundaries, and review operational charts for the workspace.

The P0 implementation must prove the workflow without adding production tenant provisioning, enterprise SSO, Microsoft Graph directory sync, billing, or deletion powers.

## Research Basis

- NIST RBAC defines access control through users, roles, permissions, operations, objects, and role activation in a session. DataSentinel uses that basis by assigning workspace members to groups that carry explicit workspace permissions instead of assigning broad rights directly to every account. Reference: https://csrc.nist.gov/Projects/role-based-access-control/faqs
- NIST's RBAC project summary describes the RBAC reference model as user assignment, permission assignment, roles, permissions, operations, and objects. DataSentinel maps users to workspace memberships, roles to workspace groups, permissions to allowed workspace actions, and objects to workspace-scoped sources, findings, admin screens, invitations, and governance records. Reference: https://csrc.nist.gov/Projects/Role-Based-Access-Control
- OWASP access-control guidance recommends deny-by-default and least privilege. DataSentinel keeps unaffiliated accounts workspace-less by default, exposes denied actions with reasons, and requires explicit invitation acceptance before workspace access. Reference: https://devguide.owasp.org/en/04-design/02-web-app-checklist/07-access-controls/
- OWASP's least-privilege principle says access should be limited to the minimum required. DataSentinel therefore separates workspace administrators, privacy reviewers, data stewards, and auditors instead of granting every signed-in account admin access. Reference: https://owasp.org/www-community/controls/Least_Privilege_Principle

## Detailed Plan

1. Add a workspace domain contract with `Workspace`, `WorkspaceMembership`, `WorkspaceGroup`, `WorkspaceInvitation`, `WorkspaceDirectory`, and `WorkspaceAdminSummary`.
2. Keep the account system separate: a newly created account has no workspace membership unless it accepts an invitation or is represented by a seeded demo admin membership.
3. Let a signed-in account create a new Workspace; the creator becomes an active `workspace_admin` member of that Workspace.
4. Use workspace groups as the P0 role mechanism:
   - `workspace_admin`: manage members, manage groups, invite members, view workspace admin charts, view audit/evaluation/governance.
   - `privacy_reviewer`: view assigned findings, submit allowed human-review decisions, view review support.
   - `data_steward`: view owned sources/findings, act on delegated stewardship decisions.
   - `auditor`: read audit, evaluation, governance, and permission boundaries without mutating workflow state.
5. Expose the Workspace permission catalog in the admin summary so administrators choose from known P0 permissions instead of typing arbitrary powers.
6. Let administrators create, rename, re-describe, re-permission, and delete Workspace groups through guarded group commands.
7. Derive workspace permission boundaries from the current membership's groups and return both allowed and denied actions.
8. Add invitation lifecycle support: generate pending invite links with explicit groups, accept invite links, reject expired/revoked/duplicate acceptance without creating extra memberships.
9. Make the top-left workspace menu data-backed: current workspace, workspace list, legacy pending invitations when available, current group labels, and link to the workspace admin surface.
10. Add `/workspace/admin` for workspace administrators. It shows member summary, groups, pending invite links, invitation creation, permission boundary, collapsed group controls, and lightweight charts using existing metrics plus workspace membership/invitation data.
11. Add `/workspace/admin/members` as a dedicated member directory with search, group/status filters, grouping, and sorting over the same admin summary membership data.
12. Keep charts deterministic and local to the P0 contract. Do not add a charting dependency; render accessible bars and progress rows with existing React/CSS.
13. Update backend demo routes and mock payloads so frontend and backend remain aligned through envelopes.
14. Add tests for workspace-less accounts, workspace creation, admin invitation creation, invitation acceptance, admin summary visibility, group customization, and member-directory browsing.

## Options

| Option | Upside | Downside | Decision |
| --- | --- | --- | --- |
| Account-only roles | Fast to implement | Violates the requirement that new accounts start outside workspaces and makes the workspace menu meaningless | Rejected |
| Full production tenant/RBAC provider | Real enterprise model | Adds tenant provisioning, directory sync, and security surface outside P0 | Rejected |
| Workspace-scoped local RBAC with invitations | Fits P0, keeps account and workspace separate, reversible | Not production authorization or enterprise SSO | Accepted |

## State Machine

### Account to Workspace Access

States:

- `account_created`
- `workspace_unassigned`
- `workspace_created`
- `invitation_pending`
- `invitation_accepted`
- `workspace_member_active`
- `membership_suspended`
- `invitation_expired`
- `invitation_revoked`

Events:

- `account_sign_in`
- `admin_generates_invite_link`
- `account_creates_workspace`
- `account_opens_invite_link`
- `account_accepts_invite_link`
- `admin_changes_groups`
- `admin_creates_group`
- `admin_updates_group`
- `admin_deletes_group`
- `admin_suspends_member`
- `invitation_expires`
- `admin_revokes_invitation`

Guards:

- Invitation creation requires `invite_workspace_members`.
- Group creation, update, and deletion require `manage_workspace_groups`.
- Group permissions must come from the exposed Workspace permission catalog.
- The `workspace_admin` group cannot be deleted and must retain admin view plus group-management permissions.
- Invitation acceptance requires a signed-in account and the invite link ID.
- Accepted, expired, or revoked invitations cannot create another membership.
- Membership group changes require `manage_workspace_members`.
- Real deletion remains denied regardless of group.

Transitions:

- `account_created -> workspace_unassigned` on first valid sign-in with no membership.
- `workspace_unassigned -> workspace_member_active` on `account_creates_workspace`; the new Workspace and admin membership are created together.
- `workspace_unassigned -> invitation_pending` when a workspace admin generates an invite link.
- `workspace_member_active -> workspace_member_active` when an admin creates or updates a Workspace group.
- `workspace_member_active -> workspace_member_active` when an admin deletes a non-admin group and group references are removed from memberships and pending invite links.
- `invitation_pending -> workspace_member_active` when a signed-in account opens and accepts the link before expiry.
- `invitation_pending -> invitation_expired` when the expiry guard fails.
- `invitation_pending -> invitation_revoked` when an admin revokes before acceptance.
- `workspace_member_active -> membership_suspended` when an admin suspends the member.
- `membership_suspended -> workspace_member_active` when an admin reactivates the member.

Side effects:

- Creating an invitation records the workspace, invite path, invited groups, inviter, expiry, and status.
- Creating a Workspace records the Workspace, default P0 groups, and one active creator membership with `workspace_admin`.
- Accepting an invitation creates one active membership and records group assignment.
- Creating a group records its Workspace, generated opaque group ID, name, description, explicit permissions, and zero initial members.
- Updating a group changes its visible name, description, and explicit permissions while preserving group ID references.
- Deleting a non-admin group removes the group ID from active memberships and invitation group lists; pending invite links with no remaining groups become revoked.
- Admin summaries recompute member counts, group counts, pending invitation counts, and chart inputs.
- Permission boundaries are recalculated from active group assignments.

Failure paths:

- Non-admin invitation attempt returns `application/problem+json` and changes no state.
- Missing Workspace name returns validation problem details and changes no state.
- Duplicate Workspace slug for the same local state returns conflict problem details and changes no state.
- Missing group assignment returns validation problem details and changes no state.
- Unknown group permission, duplicate group name, missing group name, missing group, non-admin group command, deleting `workspace_admin`, or removing required admin permissions returns problem details and changes no state.
- Duplicate, expired, revoked, or already-member acceptance returns problem details and changes no state.
- Workspace-less account receives no workflow data through normal workspace directory endpoints and sees an invitation-required UI unless it opens an invite link.

Rollback path:

1. Remove the workspace endpoints from `contracts/openapi.yaml` and `docs/API_CONTRACT.md`.
2. Remove `contracts/schemas/workspace.yaml` and workspace mock payloads.
3. Remove the frontend `/workspace/admin` route and the workspace data extension from `DataProvider`.
4. Keep existing account/session, scan, finding, review, audit, metrics, and evaluation flows unchanged.
5. Keep deletion disabled throughout rollback.

## Impact Surface

- API contract and mock payloads gain workspace directory, admin summary, group create/update/delete, invitation create, and invitation accept shapes.
- Backend local API gains workspace state and routes.
- Frontend shell consumes workspace data for the top-left workspace menu and opens the Workspace creation dialog from that menu.
- Frontend navigation gains `/workspace/admin` and a nested `/workspace/admin/members` entry.
- Frontend data context gains workspace summary, group actions, and invitation actions.
- Acceptance, PRD, TRD, governance, frontend console contract, and test cases gain workspace-admin requirements.

## Primitive Acceptance Criteria

- A newly signed-in account with no membership receives an empty workspace list and no current workspace.
- A signed-in account can open a creation dialog from the Workspace menu or no-Workspace state, create a Workspace, and becomes its active `workspace_admin` member.
- A workspace admin can see member, group, invitation, and chart data for the current workspace.
- A workspace admin can open a dedicated Members page from the sidebar or Admin Members panel and browse members with search, filtering, grouping, and sorting.
- A workspace admin can create a group by choosing a name and permissions from the exposed permission catalog.
- A workspace admin can rename a group and change its permission set; permission-boundary calculations use the updated group definition.
- A workspace admin can delete a non-admin group; members and pending invite links no longer reference it.
- Deleting the `workspace_admin` group or removing its required admin-management permissions is rejected.
- A non-admin member can see their denied admin actions instead of hidden privilege.
- A workspace admin can generate a pending invite link with one or more workspace groups.
- A signed-in account can open and accept the invite link.
- Accepting an invitation creates one active membership in the invited workspace.
- Reaccepting, accepting a revoked invitation, accepting an expired invitation, or accepting as an existing member does not create a membership.
- The workspace menu shows the current workspace when membership exists, shows invitation-required state when it does not, and opens the Workspace creation dialog from its create action.
- The admin page charts render from contract data without a new chart dependency.
- Workspace permissions do not enable real deletion, production tenant access, Microsoft Graph access, legal conclusions, or hidden powers.
