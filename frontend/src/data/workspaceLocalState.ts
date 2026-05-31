import type { MockData } from './mockApi'
import type { CreateWorkspaceInput, Workspace, WorkspaceGroup, WorkspaceGroupInput, WorkspaceMembership } from '../types'

const adminPermissions = [
  'view_workspace_admin',
  'invite_workspace_members',
  'manage_workspace_members',
  'manage_workspace_groups',
  'view_workspace_metrics',
  'view_workspace_audit',
  'view_governance',
  'view_assigned_findings',
  'view_review_support',
  'review_findings',
]

export const workspacePermissionOptions = [
  {
    permission: 'view_workspace_admin',
    label: 'View Workspace admin',
    description: 'Open the Workspace administration surface and inspect visible control-plane state.',
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
  const slug = input.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'workspace'
  const workspaceId = `ws_${slug}_${Date.now()}`
  const workspace: Workspace = {
    workspaceId,
    name: input.name,
    slug,
    status: 'active',
    plan: 'Prelaunch',
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
    groupIds: ['workspace_admin'],
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
        roles: ['workspace_admin'],
        allowedActions: adminPermissions,
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
          value: group.groupId === 'workspace_admin' ? 1 : 0,
          tone: group.groupId === 'workspace_admin' ? 'black' : 'neutral',
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

function defaultGroups(): WorkspaceGroup[] {
  return [
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
          tone: group.groupId === 'workspace_admin' ? 'black' : 'neutral',
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
