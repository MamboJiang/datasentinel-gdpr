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
3. Let a signed-in account create a new Workspace; the creator becomes an active `workspace_owner` and `workspace_admin` member of that Workspace.
4. Use workspace groups as the P0 role mechanism:
   - `workspace_owner`: highest Workspace authority; transfer owner authority, delete the Workspace record after exact-name confirmation, and retain admin membership.
   - `workspace_admin`: manage profile settings, manage members, manage groups, invite members, view workspace admin charts, view audit/evaluation/governance.
   - `privacy_reviewer`: view assigned findings, submit allowed human-review decisions, view review support.
   - `data_steward`: view owned sources/findings, act on delegated stewardship decisions.
   - `auditor`: read audit, evaluation, governance, and permission boundaries without mutating workflow state.
5. Expose the Workspace permission catalog in the admin summary so administrators choose from known P0 permissions instead of typing arbitrary powers.
6. Let administrators create, rename, re-describe, re-permission, and delete Workspace groups through guarded group commands.
7. Derive workspace permission boundaries from the current membership's groups and return both allowed and denied actions.
8. Store the current Workspace selection per account and scope sources, scans, findings, audit, metrics, and evaluation to that selected Workspace when membership exists.
9. Let administrators with `manage_workspace_members` update member group assignments and remove active members without allowing admin lockout.
10. Let Workspace owners transfer owner authority to another active member without leaving the Workspace ownerless.
11. Let Workspace owners soft-delete a Workspace only after exact-name confirmation; internal memberships and pending invitations are closed, but external source files and production tenant resources are untouched.
12. Add invitation lifecycle support: generate pending invite links with explicit non-owner groups, copy pending links, accept invite links, reject expired/revoked/duplicate acceptance without creating extra memberships.
13. Make the top-left workspace menu data-backed: current workspace, workspace list, legacy pending invitations when available, current group labels, and link to the workspace admin surface.
14. Add `/workspace/admin` for workspace administrators. It shows member summary, groups, pending invite links with copy actions, invitation creation, permission boundary, collapsed group controls, Owner-only Danger Zone, and lightweight charts using existing metrics plus workspace membership/invitation data.
15. Add `/workspace/admin/members` as a dedicated member directory with search, group/status filters, grouping, sorting, group reassignment, and member removal over the same admin summary membership data.
16. Keep charts deterministic and local to the P0 contract. Do not add a charting dependency; render accessible bars and progress rows with existing React/CSS.
17. Hide sidebar destinations whose required actions are outside the current Workspace permission boundary.
18. Update backend demo routes and mock payloads so frontend and backend remain aligned through envelopes.
19. Add tests for workspace-less accounts, workspace creation, workspace switching, workspace-scoped operational isolation, Workspace profile customization, admin invitation creation, invitation acceptance, admin summary visibility, group customization, member management, member-directory browsing, Owner transfer, and exact-name Workspace deletion.

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
- `workspace_deleted`

Events:

- `account_sign_in`
- `admin_generates_invite_link`
- `admin_copies_pending_invite_link`
- `account_creates_workspace`
- `account_opens_invite_link`
- `account_accepts_invite_link`
- `account_switches_workspace`
- `admin_changes_groups`
- `admin_changes_member_groups`
- `admin_removes_member`
- `owner_transfers_owner`
- `owner_deletes_workspace`
- `admin_creates_group`
- `admin_updates_group`
- `admin_deletes_group`
- `admin_suspends_member`
- `invitation_expires`
- `admin_revokes_invitation`

Guards:

- Invitation creation requires `invite_workspace_members`.
- Invitation group IDs cannot include `workspace_owner`; Owner authority must move through the owner-transfer command.
- Owner transfer and Workspace deletion require `manage_workspace_ownership`.
- Workspace profile setting updates require `manage_workspace_settings`.
- Group creation, update, and deletion require `manage_workspace_groups`.
- Group permissions must come from the exposed Workspace permission catalog.
- The `workspace_owner` group cannot be deleted and must retain owner-management, admin-view, settings-management, and member-management permissions.
- The `workspace_admin` group cannot be deleted and must retain admin view, settings-management, and group-management permissions.
- Invitation acceptance requires a signed-in account and the invite link ID.
- Workspace switching requires an active membership in the target Workspace.
- Accepted, expired, or revoked invitations cannot create another membership.
- Membership group changes require `manage_workspace_members`.
- Adding or removing `workspace_owner` from a member requires `manage_workspace_ownership`.
- Member removal requires `manage_workspace_members`.
- Member group changes and removal must leave at least one active `workspace_owner` member.
- Member group changes and removal must leave at least one active `workspace_admin` member.
- Admins cannot remove their own active membership.
- Workspace deletion requires an exact match against the current Workspace name.
- Real deletion remains denied regardless of group.

Transitions:

- `account_created -> workspace_unassigned` on first valid sign-in with no membership.
- `workspace_unassigned -> workspace_member_active` on `account_creates_workspace`; the new Workspace and owner/admin membership are created together.
- `workspace_unassigned -> invitation_pending` when a workspace admin generates an invite link.
- `invitation_pending -> invitation_pending` when an admin copies a pending invite link; no server state changes.
- `workspace_member_active -> workspace_member_active` on `account_switches_workspace`; only the account's selected Workspace changes.
- `workspace_member_active -> workspace_member_active` when an admin changes Workspace profile settings.
- `workspace_member_active -> workspace_member_active` when an admin creates or updates a Workspace group.
- `workspace_member_active -> workspace_member_active` when an admin deletes a non-admin group and group references are removed from memberships and pending invite links.
- `workspace_member_active -> workspace_member_active` when an admin changes a member's group assignments.
- `workspace_member_active -> workspace_member_active` when a Workspace owner transfers owner authority to another active member.
- `workspace_member_active -> membership_suspended` when an admin removes a member from active Workspace membership.
- `workspace_member_active -> workspace_deleted` when a Workspace owner confirms deletion by typing the exact Workspace name.
- `invitation_pending -> workspace_member_active` when a signed-in account opens and accepts the link before expiry.
- `invitation_pending -> invitation_expired` when the expiry guard fails.
- `invitation_pending -> invitation_revoked` when an admin revokes before acceptance.
- `workspace_member_active -> membership_suspended` when an admin suspends the member.
- `membership_suspended -> workspace_member_active` when an admin reactivates the member.

Side effects:

- Creating an invitation records the workspace, invite path, invited groups, inviter, expiry, and status.
- Copying a pending invite link writes to the user's clipboard only and does not grant access.
- Creating a Workspace records the Workspace, default P0 groups, and one active creator membership with `workspace_owner` and `workspace_admin`.
- Accepting an invitation creates one active membership and records group assignment.
- Creating a Workspace, accepting an invitation, or switching Workspaces updates the account's current Workspace selection.
- Updating Workspace profile settings changes shell display fields only; it does not alter plan, membership, source scope, or permissions.
- Operational source, scan, finding, audit, metric, and evaluation state resolves to the selected `workspace:{workspaceId}` owner scope when a current Workspace exists.
- Creating a group records its Workspace, generated opaque group ID, name, description, explicit permissions, and zero initial members.
- Updating a group changes its visible name, description, and explicit permissions while preserving group ID references.
- Deleting a non-admin group removes the group ID from active memberships and invitation group lists; pending invite links with no remaining groups become revoked.
- Updating a member changes only that member's active group IDs.
- Removing a member marks that membership removed and clears that account's current Workspace selection when it pointed at the removed Workspace.
- Transferring owner authority adds `workspace_owner` and `workspace_admin` to the target active member and removes `workspace_owner` from prior active owners.
- Deleting a Workspace marks the Workspace deleted, marks active memberships removed, revokes pending invitations, and clears current Workspace selections for affected accounts.
- Admin summaries recompute member counts, group counts, pending invitation counts, and chart inputs.
- Permission boundaries are recalculated from active group assignments.

Failure paths:

- Non-admin invitation attempt returns `application/problem+json` and changes no state.
- Missing Workspace name returns validation problem details and changes no state.
- Duplicate Workspace slug for the same local state returns conflict problem details and changes no state.
- Missing group assignment returns validation problem details and changes no state.
- Unknown group permission, duplicate group name, missing group name, missing group, non-admin group command, deleting `workspace_owner`, deleting `workspace_admin`, or removing required owner/admin permissions returns problem details and changes no state.
- Unknown member, empty member group list, unknown member group, non-admin member command, unauthorized owner change, self-removal, last-owner removal/demotion, or last-admin removal/demotion returns problem details and changes no state.
- Owner transfer to an unknown, removed, suspended, or cross-Workspace membership returns problem details and changes no state.
- Workspace deletion without owner permission or with a non-matching confirmation name returns problem details and changes no state.
- Duplicate, expired, revoked, or already-member acceptance returns problem details and changes no state.
- Switching to an unknown or non-member Workspace returns problem details and leaves the previous selection and operational state unchanged.
- Workspace-less account receives no workflow data through normal workspace directory endpoints and sees an invitation-required UI unless it opens an invite link.

Rollback path:

1. Remove the workspace endpoints from `contracts/openapi.yaml` and `docs/API_CONTRACT.md`.
2. Remove `contracts/schemas/workspace.yaml` and workspace mock payloads.
3. Remove the frontend `/workspace/admin` route and the workspace data extension from `DataProvider`.
4. Remove Owner transfer and Workspace deletion UI/actions first if only the Danger Zone needs rollback; existing member, group, and invitation flows can remain.
5. Keep existing account/session, scan, finding, review, audit, metrics, and evaluation flows unchanged.
6. Keep external source-file deletion disabled throughout rollback.

## Impact Surface

- API contract and mock payloads gain workspace directory, admin summary, profile settings, owner transfer, Workspace deletion, group create/update/delete, member update/delete, invitation create, and invitation accept shapes.
- Backend local API gains workspace state, current Workspace selection, Workspace switch, and Workspace-scoped operational owner resolution.
- Frontend shell consumes workspace data for the top-left workspace menu and opens the Workspace creation dialog from that menu.
- Frontend navigation gains `/workspace/admin`, nested `/workspace/admin/members`, and nested `/workspace/admin/groups` entries, and hides entries outside the current Workspace permission boundary.
- Frontend data context gains workspace summary, group actions, and invitation actions.
- Acceptance, PRD, TRD, governance, frontend console contract, and test cases gain workspace-admin requirements.

## Primitive Acceptance Criteria

- A newly signed-in account with no membership receives an empty workspace list and no current workspace.
- A signed-in account can open a creation dialog from the Workspace menu or no-Workspace state, create a Workspace, and becomes its active `workspace_owner` and `workspace_admin` member.
- A workspace admin can see member, group, invitation, and chart data for the current workspace.
- A workspace admin with settings permission can customize the compact Workspace label shown in the sidebar; setting it to an empty string hides the tag.
- A workspace member can switch among their Workspaces from the top-left Workspace menu.
- Switching Workspaces shows that Workspace's independent sources, findings, scan state, audit events, metrics, and evaluation state; data is not copied from the previous Workspace.
- A workspace admin can open a dedicated Members page from the sidebar or Admin Members panel and browse members with search, filtering, grouping, and sorting.
- A workspace admin can open a dedicated Group controls page from the sidebar or Admin Group controls panel and manage group definitions there.
- A workspace admin with member-management permission can update a member's groups from the Members page.
- A workspace admin with member-management permission can remove a member from the Workspace unless the target is the admin's own active membership.
- Last-admin member group changes or removals are rejected.
- Last-owner member group changes or removals are rejected.
- A workspace admin can create a group on `/workspace/admin/groups` by choosing a name and permissions from the exposed permission catalog.
- A workspace admin can rename a group and change its permission set on `/workspace/admin/groups`; permission-boundary calculations use the updated group definition.
- A workspace admin can delete a non-admin group from `/workspace/admin/groups`; members and pending invite links no longer reference it.
- Deleting the `workspace_owner` group or removing its required owner-management permissions is rejected.
- Deleting the `workspace_admin` group or removing its required admin-management permissions is rejected.
- A non-admin member can see their denied admin actions instead of hidden privilege.
- A non-admin member does not see sidebar entries for pages that require actions outside their Workspace permission boundary.
- A workspace admin can generate a pending invite link with one or more non-owner workspace groups.
- A workspace admin can copy a pending invite link directly from the invitations list.
- A signed-in account can open and accept the invite link.
- Accepting an invitation creates one active membership in the invited workspace.
- Reaccepting, accepting a revoked invitation, accepting an expired invitation, or accepting as an existing member does not create a membership.
- A workspace owner can transfer owner authority only after typing another active member's exact email and accepting a second confirmation; the target becomes both `workspace_owner` and `workspace_admin`, and prior active owners lose `workspace_owner`.
- A workspace owner can delete the Workspace only after typing the exact Workspace name and accepting a second confirmation.
- Workspace deletion removes the Workspace from visible directories, marks active memberships removed, revokes pending invite links, and clears affected current Workspace selections.
- Workspace deletion does not delete external source files, production tenant resources, or provider data.
- The workspace menu shows the current workspace when membership exists, shows invitation-required state when it does not, and opens the Workspace creation dialog from its create action.
- Sidebar groups that have nested destinations show a right-side expansion chevron.
- The admin page charts render from contract data without a new chart dependency.
- Workspace permissions do not enable real deletion, production tenant access, Microsoft Graph access, legal conclusions, or hidden powers.
