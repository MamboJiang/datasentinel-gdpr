import type { MockData } from './mockApi'
import type { CreateWorkspaceInput, Workspace, WorkspaceGroup, WorkspaceGroupInput, WorkspaceMembership } from '../types'

const adminPermissions = [
  'view_workspace_admin',
  'manage_workspace_settings',
  'invite_workspace_members',
  'manage_workspace_members',
  'manage_workspace_groups',
  'view_workspace_metrics',
  'view_workspace_audit',
  'view_governance',
  'view_assigned_findings',
  'view_review_support',
  'review_findings',
  'view_owned_sources',
]

const ownerPermissions = [
  'manage_workspace_ownership',
  ...adminPermissions,
]

export const workspacePermissionOptions = [
  {
    permission: 'manage_workspace_ownership',
    label: 'Manage Workspace owner',
    description: 'Transfer the Workspace owner role and delete the Workspace control-plane record.',
  },
  {
    permission: 'view_workspace_admin',
    label: 'View Workspace admin',
    description: 'Open the Workspace administration surface and inspect visible control-plane state.',
  },
  {
    permission: 'manage_workspace_settings',
    label: 'Manage Workspace settings',
    description: 'Change Workspace name and description shown in the application shell.',
  },
  {
    permission: 'invite_workspace_members',
    label: 'Generate invite links',
    description: 'Create pending invitation links with explicit Workspace group assignment.',
  },
  {
    permission: 'manage_workspace_members',
    label: 'Manage members',
    description: 'Change Workspace member control-plane state when member editing is exposed.',
  },
  {
    permission: 'manage_workspace_groups',
    label: 'Manage groups',
    description: 'Create, edit, and delete Workspace groups and their permission sets.',
  },
  {
    permission: 'view_workspace_metrics',
    label: 'View metrics',
    description: 'Read Workspace-level metrics and admin charts.',
  },
  {
    permission: 'view_workspace_audit',
    label: 'View audit',
    description: 'Read Workspace audit and operational evidence.',
  },
  {
    permission: 'view_governance',
    label: 'View governance',
    description: 'Read policy-pack and governance configuration state.',
  },
  {
    permission: 'view_assigned_findings',
    label: 'View assigned findings',
    description: 'Read findings assigned or delegated to the actor.',
  },
  {
    permission: 'view_review_support',
    label: 'View review support',
    description: 'Read permission-aware reviewer guidance for findings.',
  },
  {
    permission: 'review_findings',
    label: 'Review findings',
    description: 'Record supported human review decisions inside the visible permission boundary.',
  },
  {
    permission: 'view_owned_sources',
    label: 'View owned sources',
    description: 'Read source records owned or stewarded by the actor.',
  },
]

export function applyLocalWorkspaceCreation(current: MockData, input: CreateWorkspaceInput): MockData {
  const now = new Date().toISOString()
  const slug = workspaceSlug(input.name)
  const workspaceId = `ws_${slug}_${Date.now()}`
  const workspace: Workspace = {
    workspaceId,
    name: input.name,
    slug,
    status: 'active',
    plan: 'Prelaunch',
    headerLabel: 'Prelaunch',
    description: input.description || 'Privacy operations workspace',
    createdAt: now,
    memberCount: 1,
    pendingInvitationCount: 0,
  }
  const membership: WorkspaceMembership = {
    membershipId: `mem_local_${workspaceId}`,
    workspaceId,
    accountId: current.workspaceDirectory.account.accountId || 'local_creator',
    displayName: current.workspaceDirectory.account.displayName || 'Workspace creator',
    email: current.workspaceDirectory.account.email ?? null,
    groupIds: ['workspace_owner', 'workspace_admin'],
    status: 'active',
    joinedAt: now,
    invitedBy: null,
    lastActiveAt: now,
  }
  const groups = defaultGroups()

  return {
    ...current,
    workspaceDirectory: {
      ...current.workspaceDirectory,
      currentWorkspaceId: workspaceId,
      workspaces: [...current.workspaceDirectory.workspaces, workspace],
      workspaceRequired: false,
    },
    workspaceAdmin: {
      ...current.workspaceAdmin,
      workspace,
      currentMembership: membership,
      permissionBoundary: {
        ...current.workspaceAdmin.permissionBoundary,
        actorId: membership.accountId,
        workspaceId,
        roles: ['workspace_owner', 'workspace_admin'],
        allowedActions: ownerPermissions,
        deniedActions: [
          { action: 'execute_real_deletion', reason: 'Real deletion is disabled in P0.' },
          { action: 'sync_enterprise_directory', reason: 'Production directory and tenant sync are out of scope for P0.' },
        ],
        visibleScopes: [`workspace:${workspaceId}`],
        boundaryFingerprint: `local:${workspaceId}`,
        evaluatedAt: now,
      },
      availablePermissions: workspacePermissionOptions,
      groups,
      members: [membership],
      invitations: [],
      charts: {
        ...current.workspaceAdmin.charts,
        membersByGroup: groups.map((group) => ({
          label: group.name,
          value: membership.groupIds.includes(group.groupId) ? 1 : 0,
          tone: groupTone(group.groupId),
        })),
        invitationStatus: [
          { label: 'Pending', value: 0, tone: 'yellow' },
          { label: 'Accepted', value: 0, tone: 'green' },
          { label: 'Expired', value: 0, tone: 'neutral' },
        ],
      },
    },
  }
}

export function applyLocalWorkspaceSettingsUpdate(
  current: MockData,
  workspaceId: string,
  settings: { description?: string; headerLabel?: string; name?: string },
): MockData {
  const updateWorkspace = (workspace: Workspace) => (
    workspace.workspaceId === workspaceId
      ? {
          ...workspace,
          description: settings.description ?? workspace.description,
          headerLabel: settings.headerLabel ?? workspace.headerLabel,
          name: settings.name ?? workspace.name,
          slug: settings.name ? workspaceSlug(settings.name) : workspace.slug,
        }
      : workspace
  )

  return {
    ...current,
    workspaceDirectory: {
      ...current.workspaceDirectory,
      workspaces: current.workspaceDirectory.workspaces.map(updateWorkspace),
    },
    workspaceAdmin: {
      ...current.workspaceAdmin,
      workspace: current.workspaceAdmin.workspace ? updateWorkspace(current.workspaceAdmin.workspace) : null,
    },
  }
}

function workspaceSlug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'workspace'
}

export function buildLocalWorkspaceGroup(current: MockData, input: WorkspaceGroupInput): WorkspaceGroup {
  return {
    workspaceId: input.workspaceId,
    groupId: localGroupId(input.name, current.workspaceAdmin.groups),
    name: input.name.trim(),
    description: input.description?.trim() ?? '',
    permissions: uniquePermissions(input.permissions),
    memberCount: 0,
  }
}

export function applyLocalWorkspaceGroupCreation(current: MockData, group: WorkspaceGroup): MockData {
  return withWorkspaceGroups(current, [...current.workspaceAdmin.groups, group])
}

export function applyLocalWorkspaceGroupUpdate(current: MockData, group: WorkspaceGroup): MockData {
  return withWorkspaceGroups(current, current.workspaceAdmin.groups.map((item) => (
    item.groupId === group.groupId ? { ...group, memberCount: item.memberCount } : item
  )))
}

export function applyLocalWorkspaceGroupDeletion(current: MockData, workspaceId: string, groupId: string): MockData {
  const groups = current.workspaceAdmin.groups.filter((group) => group.groupId !== groupId)
  const members = current.workspaceAdmin.members.map((member) => (
    member.workspaceId === workspaceId
      ? { ...member, groupIds: member.groupIds.filter((item) => item !== groupId) }
      : member
  ))
  const invitations = current.workspaceAdmin.invitations.map((invitation) => {
    if (invitation.workspaceId !== workspaceId || !invitation.groupIds.includes(groupId)) {
      return invitation
    }

    const groupIds = invitation.groupIds.filter((item) => item !== groupId)
    return {
      ...invitation,
      groupIds,
      status: invitation.status === 'pending' && groupIds.length === 0 ? 'revoked' : invitation.status,
    }
  })

  return withWorkspaceGroups({
    ...current,
    workspaceAdmin: {
      ...current.workspaceAdmin,
      members,
      invitations,
    },
  }, groups)
}

export function applyLocalWorkspaceMemberUpdate(current: MockData, workspaceId: string, membershipId: string, groupIds: string[]): MockData {
  const members = current.workspaceAdmin.members.map((member) => (
    member.workspaceId === workspaceId && member.membershipId === membershipId
      ? { ...member, groupIds }
      : member
  ))
  return withWorkspaceMembers(current, members)
}

export function applyLocalWorkspaceMemberDeletion(current: MockData, workspaceId: string, membershipId: string): MockData {
  const members = current.workspaceAdmin.members.filter((member) => (
    !(member.workspaceId === workspaceId && member.membershipId === membershipId)
  ))
  return withWorkspaceMembers(current, members)
}

export function applyLocalWorkspaceOwnerTransfer(current: MockData, workspaceId: string, membershipId: string): MockData {
  const members = current.workspaceAdmin.members.map((member) => {
    if (member.workspaceId !== workspaceId) {
      return member
    }

    if (member.membershipId === membershipId) {
      return { ...member, groupIds: Array.from(new Set([...member.groupIds, 'workspace_owner', 'workspace_admin'])) }
    }

    return { ...member, groupIds: member.groupIds.filter((groupId) => groupId !== 'workspace_owner') }
  })
  return withWorkspaceMembers(current, members)
}

export function applyLocalWorkspaceDeletion(current: MockData, workspaceId: string): MockData {
  const workspaces = current.workspaceDirectory.workspaces.filter((workspace) => workspace.workspaceId !== workspaceId)
  return {
    ...current,
    workspaceDirectory: {
      ...current.workspaceDirectory,
      currentWorkspaceId: workspaces[0]?.workspaceId ?? null,
      workspaces,
      workspaceRequired: workspaces.length === 0,
    },
    workspaceAdmin: workspaces.length === 0 ? {
      ...current.workspaceAdmin,
      workspace: null,
      currentMembership: null,
      groups: [],
      members: [],
      invitations: [],
    } : current.workspaceAdmin,
  }
}

function defaultGroups(): WorkspaceGroup[] {
  return [
    {
      groupId: 'workspace_owner',
      name: 'Workspace owners',
      description: 'Highest Workspace authority for owner transfer and Workspace deletion.',
      permissions: ownerPermissions,
      memberCount: 1,
    },
    {
      groupId: 'workspace_admin',
      name: 'Workspace admins',
      description: 'Can manage Workspace members, groups, invitations, audit, governance, and metrics.',
      permissions: adminPermissions,
      memberCount: 1,
    },
    {
      groupId: 'privacy_reviewer',
      name: 'Privacy reviewers',
      description: 'Can review assigned findings with visible permission boundaries.',
      permissions: ['view_assigned_findings', 'view_review_support', 'review_findings'],
      memberCount: 0,
    },
    {
      groupId: 'data_steward',
      name: 'Data stewards',
      description: 'Can steward owned sources and delegated findings.',
      permissions: ['view_owned_sources', 'view_assigned_findings', 'review_findings'],
      memberCount: 0,
    },
    {
      groupId: 'auditor',
      name: 'Auditors',
      description: 'Can inspect governance, audit, and evaluation evidence without mutating workflow state.',
      permissions: ['view_workspace_audit', 'view_workspace_metrics', 'view_governance'],
      memberCount: 0,
    },
  ]
}

function withWorkspaceGroups(current: MockData, groups: WorkspaceGroup[]): MockData {
  return {
    ...current,
    workspaceAdmin: {
      ...current.workspaceAdmin,
      groups,
      charts: {
        ...current.workspaceAdmin.charts,
        membersByGroup: groups.map((group) => ({
          label: group.name,
          value: group.memberCount,
          tone: groupTone(group.groupId),
        })),
      },
    },
  }
}

function withWorkspaceMembers(current: MockData, members: WorkspaceMembership[]): MockData {
  const groups = current.workspaceAdmin.groups.map((group) => ({
    ...group,
    memberCount: members.filter((member) => member.groupIds.includes(group.groupId)).length,
  }))
  return {
    ...current,
    workspaceAdmin: {
      ...current.workspaceAdmin,
      groups,
      members,
      charts: {
        ...current.workspaceAdmin.charts,
        membersByGroup: groups.map((group) => ({
          label: group.name,
          value: group.memberCount,
          tone: groupTone(group.groupId),
        })),
      },
    },
  }
}

function localGroupId(name: string, groups: WorkspaceGroup[]) {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'group'
  const base = `custom_${slug}`
  const existing = new Set(groups.map((group) => group.groupId))
  let candidate = base
  let suffix = 2
  while (existing.has(candidate)) {
    candidate = `${base}_${suffix}`
    suffix += 1
  }
  return candidate
}

function uniquePermissions(permissions: string[]) {
  const valid = new Set(workspacePermissionOptions.map((option) => option.permission))
  return Array.from(new Set(permissions.filter((permission) => valid.has(permission))))
}

function groupTone(groupId: string) {
  return groupId === 'workspace_owner' || groupId === 'workspace_admin' ? 'black' : 'neutral'
}
