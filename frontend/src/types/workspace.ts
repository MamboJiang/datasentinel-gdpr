export type Workspace = {
  workspaceId: string
  name: string
  slug: string
  status: string
  plan: string
  description?: string
  createdAt?: string
  memberCount: number
  pendingInvitationCount: number
}

export type WorkspaceGroup = {
  workspaceId?: string
  groupId: string
  name: string
  description?: string
  permissions: string[]
  memberCount: number
}

export type WorkspacePermissionOption = {
  permission: string
  label: string
  description: string
}

export type WorkspaceMembership = {
  membershipId: string
  workspaceId: string
  accountId: string
  displayName: string
  email?: string | null
  groupIds: string[]
  status: string
  joinedAt: string
  invitedBy?: string | null
  lastActiveAt?: string | null
}

export type WorkspaceInvitation = {
  invitationId: string
  workspaceId: string
  invitePath: string
  email?: string | null
  groupIds: string[]
  status: string
  invitedBy: string
  invitedByDisplayName?: string
  createdAt: string
  expiresAt: string
  acceptedAt?: string | null
}

export type WorkspacePermissionBoundary = {
  actorId: string
  workspaceId: string | null
  roles: string[]
  allowedActions: string[]
  deniedActions: {
    action: string
    reason: string
  }[]
  visibleScopes: string[]
  boundaryFingerprint?: string
  evaluatedAt?: string
}

export type WorkspaceChartDatum = {
  label: string
  value: number
  tone?: string
}

export type WorkspaceAdminCharts = {
  membersByGroup: WorkspaceChartDatum[]
  invitationStatus: WorkspaceChartDatum[]
  reviewLoad: WorkspaceChartDatum[]
  riskOverview: WorkspaceChartDatum[]
  scanCoverage: WorkspaceChartDatum[]
}

export type WorkspaceDirectory = {
  account: {
    accountId: string
    displayName: string
    email?: string | null
  }
  currentWorkspaceId: string | null
  workspaces: Workspace[]
  pendingInvitations: WorkspaceInvitation[]
  workspaceRequired: boolean
}

export type WorkspaceAdminSummary = {
  workspace: Workspace | null
  currentMembership: WorkspaceMembership | null
  permissionBoundary: WorkspacePermissionBoundary
  availablePermissions: WorkspacePermissionOption[]
  groups: WorkspaceGroup[]
  members: WorkspaceMembership[]
  invitations: WorkspaceInvitation[]
  charts: WorkspaceAdminCharts
}

export type CreateWorkspaceInvitationInput = {
  workspaceId: string
  groupIds: string[]
}

export type CreateWorkspaceInput = {
  name: string
  description?: string
}

export type WorkspaceGroupInput = {
  workspaceId: string
  name: string
  description?: string
  permissions: string[]
}

export type UpdateWorkspaceGroupInput = WorkspaceGroupInput & {
  groupId: string
}

export type DeleteWorkspaceGroupInput = {
  workspaceId: string
  groupId: string
}
