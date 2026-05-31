import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { DataContext, type DataContextValue } from './DataContext'
import { getEmptyData } from './emptyData'
import { recordHumanReviewDecision } from './humanReviewDecision'
import { getInitialMockData } from './mockApi'
import { buildReviewSupport } from './reviewSupport'
import { completeScanWorkflow, getSourceConnectionMessage, startScanWorkflow, type StartScanOptions } from './scanWorkflow'
import {
  applyLocalWorkspaceCreation,
  applyLocalWorkspaceGroupCreation,
  applyLocalWorkspaceGroupDeletion,
  applyLocalWorkspaceGroupUpdate,
  applyLocalWorkspaceDeletion,
  applyLocalWorkspaceMemberDeletion,
  applyLocalWorkspaceMemberUpdate,
  applyLocalWorkspaceOwnerTransfer,
  applyLocalWorkspaceSettingsUpdate,
  buildLocalWorkspaceGroup,
} from './workspaceLocalState'
import {
  acceptServerWorkspaceInvitation,
  createServerWorkspaceGroup,
  createServerSource,
  createServerWorkspace,
  createServerWorkspaceInvitation,
  deleteServerWorkspace,
  deleteServerWorkspaceMember,
  deleteServerWorkspaceGroup,
  deleteServerSource,
  getServerReviewSupport,
  isApiRequestError,
  loadServerData,
  reviewServerFinding,
  startServerScan,
  switchServerWorkspace,
  transferServerWorkspaceOwner,
  testServerSourceConnection,
  updateServerWorkspaceMember,
  updateServerWorkspaceGroup,
  updateServerWorkspaceSettings,
  updateServerSource,
  type CreateSourceInput,
  type UpdateSourceInput,
} from './serverApi'
import type {
  CreateWorkspaceInvitationInput,
  CreateWorkspaceInput,
  DeleteWorkspaceGroupInput,
  DeleteWorkspaceInput,
  DeleteWorkspaceMemberInput,
  Finding,
  ReviewInput,
  ReviewSupport,
  UpdateWorkspaceGroupInput,
  UpdateWorkspaceMemberInput,
  UpdateWorkspaceSettingsInput,
  TransferWorkspaceOwnerInput,
  WorkspaceGroup,
  WorkspaceGroupInput,
  WorkspaceInvitation,
} from '../types'

const localMocksEnabled = import.meta.env.VITE_DATASENTINEL_ENABLE_LOCAL_MOCKS === 'true'

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState(localMocksEnabled ? getInitialMockData : getEmptyData)
  const [reviewSupportByFindingId, setReviewSupportByFindingId] = useState<Record<string, ReviewSupport>>({})
  const [notifications, setNotifications] = useState<DataContextValue['notifications']>([])
  const [serverConnection, setServerConnection] = useState<DataContextValue['serverConnection']>({
    checkedAt: null,
    message: 'Checking project server.',
    status: 'checking',
  })
  const [runtimeAuthorizedSourceIds, setRuntimeAuthorizedSourceIds] = useState<string[]>([])
  const scanTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const serverAvailable = useRef(false)
  const googleDriveAccessTokens = useRef<Record<string, string>>({})

  function notify(message: string) {
    setNotifications((current) => [
      {
        id: `notification_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        message,
        createdAt: new Date().toISOString(),
      },
      ...current,
    ].slice(0, 50))
  }

  const markServerConnection = useCallback((status: DataContextValue['serverConnection']['status'], message: string) => {
    serverAvailable.current = status === 'connected'
    setServerConnection({
      checkedAt: new Date().toISOString(),
      message,
      status,
    })
  }, [])

  const markServerConnected = useCallback(() => {
    markServerConnection('connected', 'Project server connected.')
  }, [markServerConnection])

  const markServerUnavailable = useCallback(() => {
    markServerConnection('disconnected', 'Project server unavailable.')
  }, [markServerConnection])

  function notifyApiRejection(error: unknown, fallbackMessage: string) {
    notify(error instanceof Error ? error.message : fallbackMessage)
  }

  function shouldUseLocalFallback(error: unknown): boolean {
    return !isApiRequestError(error)
  }

  function forgetRuntimeAuthorization(sourceId: string) {
    delete googleDriveAccessTokens.current[sourceId]
    setRuntimeAuthorizedSourceIds((current) => current.filter((candidate) => candidate !== sourceId))
  }

  function rememberRuntimeAuthorization(sourceId: string) {
    setRuntimeAuthorizedSourceIds((current) => current.includes(sourceId) ? current : [...current, sourceId])
  }

  useEffect(() => {
    let active = true
    const fallback = localMocksEnabled ? getInitialMockData() : getEmptyData()

    loadServerData(fallback)
      .then((serverData) => {
        if (!active) {
          return
        }

        markServerConnected()
        setData(serverData)
        setReviewSupportByFindingId(serverData.reviewSupport.findingId ? { [serverData.reviewSupport.findingId]: serverData.reviewSupport } : {})
      })
      .catch(() => {
        if (!active) {
          return
        }

        markServerUnavailable()
        if (localMocksEnabled) {
          setData(fallback)
        }
      })

    return () => {
      active = false

      if (scanTimer.current) {
        clearTimeout(scanTimer.current)
      }
    }
  }, [markServerConnected, markServerUnavailable])

  async function startScan(options: StartScanOptions) {
    const sourceToken = options.sourceId ? googleDriveAccessTokens.current[options.sourceId] : undefined
    const scanOptions = sourceToken && !options.googleDriveAccessToken
      ? { ...options, googleDriveAccessToken: sourceToken }
      : options

    if (serverAvailable.current) {
      try {
        const result = await startServerScan(scanOptions)

        if (scanTimer.current) {
          clearTimeout(scanTimer.current)
        }

        setData((current) => ({
          ...current,
          meta: result.meta,
          scan: result.data,
        }))
        notify(`${scanOptions.scanType === 'full' ? 'Full' : 'Delta'} scan started on the project server.`)
        scanTimer.current = setTimeout(() => {
          refreshServerData(`${scanOptions.scanType === 'full' ? 'Full' : 'Delta'} scan completed.`)
          scanTimer.current = null
        }, scanOptions.scanType === 'full' ? 2400 : 2000)
        return
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          if (scanOptions.sourceId && isGoogleDriveSource(scanOptions.sourceId)) {
            forgetRuntimeAuthorization(scanOptions.sourceId)
          }
          notifyApiRejection(error, 'Scan was rejected by the project server.')
          return
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local mock workflow.')
      }
    }

    startLocalScan(scanOptions)
  }

  function startLocalScan(options: StartScanOptions) {
    const result = startScanWorkflow(data, {
      ...options,
      actorId: 'user_demo_admin',
      auditEventId: `audit_${Date.now()}`,
      occurredAt: new Date().toISOString(),
    })

    if (!result.accepted) {
      notify(result.toast)
      return
    }

    if (scanTimer.current) {
      clearTimeout(scanTimer.current)
    }

    setData(result.data)
    notify(result.toast)

    scanTimer.current = setTimeout(() => {
      setData((current) => completeScanWorkflow(current, {
        auditEventId: `audit_${Date.now()}`,
        occurredAt: new Date().toISOString(),
        scanId: result.scanId,
      }))
      notify(`${options.scanType === 'full' ? 'Full' : 'Delta'} scan completed.`)
      scanTimer.current = null
    }, result.completionDelayMs)
  }

  async function testSourceConnection(sourceId: string) {
    if (serverAvailable.current) {
      try {
        const result = await testServerSourceConnection(sourceId)
        const diagnostics = result.data.diagnostics?.map((item) => item.message).filter(Boolean).join(' ')
        notify(`${result.data.name ?? sourceId} connection: ${result.data.connectionStatus}.${diagnostics ? ` ${diagnostics}` : ''}`)
        return
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Source connection check was rejected by the project server.')
          return
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local source check.')
      }
    }

    const source = data.sources.find((candidate) => candidate.sourceId === sourceId)
    notify(getSourceConnectionMessage(source, data.governanceConfig))
  }

  async function createSource(input: CreateSourceInput) {
    if (!serverAvailable.current) {
      notify('Project server unavailable; source registration requires the API server.')
      return
    }

    try {
      const result = await createServerSource(input)
      if (input.googleDriveAccessToken) {
        googleDriveAccessTokens.current[result.data.sourceId] = input.googleDriveAccessToken
        rememberRuntimeAuthorization(result.data.sourceId)
      }
      setData((current) => ({
        ...current,
        meta: result.meta,
        sources: [
          ...current.sources.filter((source) => source.sourceId !== result.data.sourceId),
          result.data,
        ],
      }))
      notify(`${result.data.name} registered. Test the connection before scanning.`)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Source registration failed.')
    }
  }

  async function updateSource(input: UpdateSourceInput) {
    if (!serverAvailable.current) {
      notify('Project server unavailable; Source assignment requires the API server.')
      return
    }

    try {
      const result = await updateServerSource(input)
      await refreshServerData(`${result.data.name} Source owner updated.`)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Source update failed.')
    }
  }

  async function deleteSource(sourceId: string) {
    if (!serverAvailable.current) {
      notify('Project server unavailable; source deletion requires the API server.')
      return
    }

    try {
      const result = await deleteServerSource(sourceId)
      forgetRuntimeAuthorization(sourceId)
      await refreshServerData(`${result.data.name} source registration deleted.`)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Source deletion failed.')
    }
  }

  async function reviewFinding(input: ReviewInput) {
    if (serverAvailable.current) {
      try {
        await reviewServerFinding(input)
        await refreshServerData('Review decision recorded. Deletion remains simulated.')
        return
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Review decision was rejected by the project server.')
          return
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local review workflow.')
      }
    }

    const occurredAt = new Date().toISOString()
    const finding = getFinding(input.findingId)
    const reviewSupport = finding
      ? buildReviewSupport({
          actorId: input.actorId,
          finding,
          governanceConfig: data.governanceConfig,
          occurredAt,
          workspaceMembers: data.workspaceAdmin.members,
        })
      : data.reviewSupport
    const result = recordHumanReviewDecision(data, {
      ...input,
      auditEventId: `audit_${Date.now()}`,
      occurredAt,
      reviewId: `review_${Date.now()}`,
      reviewSupportRulesFingerprint: data.scan.reviewSupport?.supportRulesFingerprint,
    }, reviewSupport)

    if (!result.accepted) {
      notify(result.reason)
      return
    }

    setData(result.data)
    notify(result.toast)
  }

  async function createWorkspace(input: CreateWorkspaceInput) {
    if (serverAvailable.current) {
      try {
        await createServerWorkspace(input)
        await refreshServerData('Workspace created. You are now a Workspace owner and admin.')
        return
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace creation was rejected by the project server.')
          return
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    setData((current) => applyLocalWorkspaceCreation(current, input))
    notify('Workspace created in local mock state. You are now a Workspace owner and admin.')
  }

  async function switchWorkspace(workspaceId: string): Promise<boolean> {
    if (workspaceId === data.workspaceDirectory.currentWorkspaceId) {
      return true
    }

    if (serverAvailable.current) {
      try {
        await switchServerWorkspace(workspaceId)
        await refreshServerData('Workspace switched.')
        return true
      } catch (error) {
        notify(error instanceof Error ? error.message : 'Workspace switch failed.')
        return false
      }
    }

    const workspace = data.workspaceDirectory.workspaces.find((candidate) => candidate.workspaceId === workspaceId)
    if (!workspace) {
      notify('Workspace membership is required.')
      return false
    }

    setData((current) => ({
      ...current,
      workspaceDirectory: {
        ...current.workspaceDirectory,
        currentWorkspaceId: workspaceId,
      },
      workspaceAdmin: {
        ...current.workspaceAdmin,
        workspace,
      },
    }))
    notify('Workspace switched in local mock state.')
    return true
  }

  async function updateWorkspaceSettings(input: UpdateWorkspaceSettingsInput): Promise<boolean> {
    const name = input.name?.trim().replace(/\s+/g, ' ')
    const description = input.description?.trim().replace(/\s+/g, ' ')
    const headerLabel = input.headerLabel?.trim().replace(/\s+/g, ' ')

    if (input.name !== undefined && !name) {
      notify('Workspace name is required.')
      return false
    }

    if (name && name.length > 80) {
      notify('Workspace name must be 80 characters or fewer.')
      return false
    }

    if (description && description.length > 240) {
      notify('Workspace description must be 240 characters or fewer.')
      return false
    }

    if (headerLabel !== undefined && headerLabel.length > 24) {
      notify('Workspace header label must be 24 characters or fewer.')
      return false
    }

    if (serverAvailable.current) {
      try {
        await updateServerWorkspaceSettings({ ...input, description, headerLabel, name })
        await refreshServerData('Workspace profile updated.')
        return true
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace settings update was rejected by the project server.')
          return false
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceSettings()) {
      notify('Workspace settings permission is required.')
      return false
    }

    setData((current) => applyLocalWorkspaceSettingsUpdate(current, input.workspaceId, { description, headerLabel, name }))
    notify('Workspace profile updated in local mock state.')
    return true
  }

  async function createWorkspaceInvitation(input: CreateWorkspaceInvitationInput) {
    if (serverAvailable.current) {
      try {
        const result = await createServerWorkspaceInvitation(input)
        await refreshServerData('Workspace invitation link created.')
        return result.data
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace invitation was rejected by the project server.')
          return null
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!data.workspaceAdmin.permissionBoundary.allowedActions.includes('invite_workspace_members')) {
      notify('Workspace admin permission is required.')
      return null
    }

    const invitationId = `invite_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    const invitation: WorkspaceInvitation = {
      invitationId,
      workspaceId: input.workspaceId,
      invitePath: `/workspace/invitations/${invitationId}`,
      groupIds: input.groupIds,
      status: 'pending',
      invitedBy: data.workspaceAdmin.currentMembership?.accountId ?? 'local_admin',
      invitedByDisplayName: data.workspaceAdmin.currentMembership?.displayName ?? 'Workspace admin',
      createdAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      acceptedAt: null,
    }

    setData((current) => ({
      ...current,
      workspaceAdmin: {
        ...current.workspaceAdmin,
        invitations: [invitation, ...current.workspaceAdmin.invitations],
      },
      workspaceDirectory: {
        ...current.workspaceDirectory,
        workspaces: current.workspaceDirectory.workspaces.map((workspace) => (
          workspace.workspaceId === input.workspaceId
            ? { ...workspace, pendingInvitationCount: workspace.pendingInvitationCount + 1 }
            : workspace
        )),
      },
    }))
    notify('Workspace invitation link created in local mock state.')
    return invitation
  }

  async function acceptWorkspaceInvitation(invitationId: string) {
    if (serverAvailable.current) {
      try {
        const result = await acceptServerWorkspaceInvitation(invitationId)
        await refreshServerData('Workspace invitation accepted.')
        setData((current) => ({ ...current, workspaceDirectory: result.data, meta: result.meta }))
        return true
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace invitation acceptance was rejected by the project server.')
          return false
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    const invitation = data.workspaceDirectory.pendingInvitations.find((item) => item.invitationId === invitationId)
      ?? data.workspaceAdmin.invitations.find((item) => item.invitationId === invitationId)

    if (!invitation) {
      notify('Workspace invitation is not available for this account.')
      return false
    }

    if (data.workspaceDirectory.workspaces.some((workspace) => workspace.workspaceId === invitation.workspaceId)) {
      notify('This account is already a member of that Workspace.')
      return false
    }

    setData((current) => ({
      ...current,
      workspaceAdmin: {
        ...current.workspaceAdmin,
        invitations: current.workspaceAdmin.invitations.map((item) => (
          item.invitationId === invitation.invitationId
            ? { ...item, acceptedAt: new Date().toISOString(), status: 'accepted' }
            : item
        )),
      },
      workspaceDirectory: {
        ...current.workspaceDirectory,
        currentWorkspaceId: invitation.workspaceId,
        pendingInvitations: current.workspaceDirectory.pendingInvitations.filter((item) => item.invitationId !== invitationId),
        workspaceRequired: false,
      },
    }))
    notify('Workspace invitation accepted in local mock state.')
    return true
  }

  async function createWorkspaceGroup(input: WorkspaceGroupInput): Promise<WorkspaceGroup | null> {
    if (serverAvailable.current) {
      try {
        const result = await createServerWorkspaceGroup(input)
        await refreshServerData('Workspace group created.')
        return result.data
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace group creation was rejected by the project server.')
          return null
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceGroups()) {
      notify('Workspace group management permission is required.')
      return null
    }

    const group = buildLocalWorkspaceGroup(data, input)
    setData((current) => applyLocalWorkspaceGroupCreation(current, group))
    notify('Workspace group created in local mock state.')
    return group
  }

  async function updateWorkspaceGroup(input: UpdateWorkspaceGroupInput): Promise<WorkspaceGroup | null> {
    if (serverAvailable.current) {
      try {
        const result = await updateServerWorkspaceGroup(input)
        await refreshServerData('Workspace group updated.')
        return result.data
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace group update was rejected by the project server.')
          return null
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceGroups()) {
      notify('Workspace group management permission is required.')
      return null
    }

    if (input.groupId === 'workspace_owner' && !canManageWorkspaceOwnership()) {
      notify('Workspace owner permission is required.')
      return null
    }

    if (input.groupId === 'workspace_owner' && (!input.permissions.includes('manage_workspace_ownership') || !input.permissions.includes('view_workspace_admin') || !input.permissions.includes('manage_workspace_members'))) {
      notify('Workspace owners must retain owner, admin view, and member management permissions.')
      return null
    }

    if (input.groupId === 'workspace_admin' && (!input.permissions.includes('view_workspace_admin') || !input.permissions.includes('manage_workspace_groups'))) {
      notify('Workspace admins must retain admin view and group management permissions.')
      return null
    }

    const existing = data.workspaceAdmin.groups.find((group) => group.groupId === input.groupId)
    if (!existing) {
      notify('Workspace group was not found.')
      return null
    }

    const group: WorkspaceGroup = {
      ...existing,
      name: input.name.trim(),
      description: input.description?.trim() ?? '',
      permissions: Array.from(new Set(input.permissions)),
    }
    setData((current) => applyLocalWorkspaceGroupUpdate(current, group))
    notify('Workspace group updated in local mock state.')
    return group
  }

  async function deleteWorkspaceGroup(input: DeleteWorkspaceGroupInput): Promise<boolean> {
    if (serverAvailable.current) {
      try {
        await deleteServerWorkspaceGroup(input)
        await refreshServerData('Workspace group deleted.')
        return true
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace group deletion was rejected by the project server.')
          return false
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceGroups()) {
      notify('Workspace group management permission is required.')
      return false
    }

    if (input.groupId === 'workspace_owner' || input.groupId === 'workspace_admin') {
      notify(`${input.groupId === 'workspace_owner' ? 'Workspace owner' : 'Workspace admin'} group cannot be deleted.`)
      return false
    }

    setData((current) => applyLocalWorkspaceGroupDeletion(current, input.workspaceId, input.groupId))
    notify('Workspace group deleted in local mock state.')
    return true
  }

  async function updateWorkspaceMember(input: UpdateWorkspaceMemberInput): Promise<boolean> {
    if (serverAvailable.current) {
      try {
        await updateServerWorkspaceMember(input)
        await refreshServerData('Workspace member groups updated.')
        return true
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace member update was rejected by the project server.')
          return false
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceMembers()) {
      notify('Workspace member management permission is required.')
      return false
    }

    const groupIds = Array.from(new Set(input.groupIds))
    const validGroupIds = new Set(data.workspaceAdmin.groups.map((group) => group.groupId))
    if (!groupIds.length || groupIds.some((groupId) => !validGroupIds.has(groupId))) {
      notify('Select at least one valid Workspace group.')
      return false
    }

    const existingMember = data.workspaceAdmin.members.find((member) => member.membershipId === input.membershipId)
    const ownerChanged = Boolean(existingMember?.groupIds.includes('workspace_owner')) !== groupIds.includes('workspace_owner')
    if (ownerChanged && !canManageWorkspaceOwnership()) {
      notify('Workspace owner permission is required.')
      return false
    }

    if (!hasWorkspaceOwnerAfterMemberChange(input.membershipId, groupIds)) {
      notify('At least one active Workspace owner member is required.')
      return false
    }

    if (!hasWorkspaceAdminAfterMemberChange(input.membershipId, groupIds)) {
      notify('At least one active Workspace admin member is required.')
      return false
    }

    setData((current) => applyLocalWorkspaceMemberUpdate(current, input.workspaceId, input.membershipId, groupIds))
    notify('Workspace member groups updated in local mock state.')
    return true
  }

  async function deleteWorkspaceMember(input: DeleteWorkspaceMemberInput): Promise<boolean> {
    if (serverAvailable.current) {
      try {
        await deleteServerWorkspaceMember(input)
        await refreshServerData('Workspace member removed.')
        return true
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace member removal was rejected by the project server.')
          return false
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceMembers()) {
      notify('Workspace member management permission is required.')
      return false
    }

    const member = data.workspaceAdmin.members.find((candidate) => candidate.membershipId === input.membershipId)
    if (!member) {
      notify('Workspace member was not found.')
      return false
    }

    if (member.accountId === data.workspaceAdmin.currentMembership?.accountId) {
      notify('Workspace admins cannot remove their own active membership.')
      return false
    }

    if (member.groupIds.includes('workspace_owner') && !canManageWorkspaceOwnership()) {
      notify('Workspace owner permission is required.')
      return false
    }

    if (!hasWorkspaceOwnerAfterMemberRemoval(input.membershipId)) {
      notify('At least one active Workspace owner member is required.')
      return false
    }

    if (!hasWorkspaceAdminAfterMemberRemoval(input.membershipId)) {
      notify('At least one active Workspace admin member is required.')
      return false
    }

    setData((current) => applyLocalWorkspaceMemberDeletion(current, input.workspaceId, input.membershipId))
    notify('Workspace member removed in local mock state.')
    return true
  }

  async function transferWorkspaceOwner(input: TransferWorkspaceOwnerInput): Promise<boolean> {
    if (serverAvailable.current) {
      try {
        await transferServerWorkspaceOwner(input)
        await refreshServerData('Workspace owner transferred.')
        return true
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace owner transfer was rejected by the project server.')
          return false
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceOwnership()) {
      notify('Workspace owner permission is required.')
      return false
    }

    const member = data.workspaceAdmin.members.find((candidate) => candidate.membershipId === input.membershipId)
    if (!member) {
      notify('Workspace member was not found.')
      return false
    }

    setData((current) => applyLocalWorkspaceOwnerTransfer(current, input.workspaceId, input.membershipId))
    notify('Workspace owner transferred in local mock state.')
    return true
  }

  async function deleteWorkspace(input: DeleteWorkspaceInput): Promise<boolean> {
    if (serverAvailable.current) {
      try {
        await deleteServerWorkspace(input)
        await refreshServerData('Workspace deleted.')
        return true
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Workspace deletion was rejected by the project server.')
          return false
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceOwnership()) {
      notify('Workspace owner permission is required.')
      return false
    }

    if (input.workspaceName !== data.workspaceAdmin.workspace?.name) {
      notify('Workspace name confirmation must match exactly.')
      return false
    }

    setData((current) => applyLocalWorkspaceDeletion(current, input.workspaceId))
    notify('Workspace deleted in local mock state.')
    return true
  }

  function canManageWorkspaceGroups() {
    return data.workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_groups')
  }

  function canManageWorkspaceSettings() {
    return data.workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_settings')
  }

  function canManageWorkspaceMembers() {
    return data.workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_members')
  }

  function canManageWorkspaceOwnership() {
    return data.workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_ownership')
  }

  function hasWorkspaceAdminAfterMemberChange(membershipId: string, groupIds: string[]) {
    return data.workspaceAdmin.members.some((member) => (
      member.status === 'active'
      && (member.membershipId === membershipId ? groupIds : member.groupIds).includes('workspace_admin')
    ))
  }

  function hasWorkspaceOwnerAfterMemberChange(membershipId: string, groupIds: string[]) {
    return data.workspaceAdmin.members.some((member) => (
      member.status === 'active'
      && (member.membershipId === membershipId ? groupIds : member.groupIds).includes('workspace_owner')
    ))
  }

  function hasWorkspaceAdminAfterMemberRemoval(membershipId: string) {
    return data.workspaceAdmin.members.some((member) => (
      member.status === 'active'
      && member.membershipId !== membershipId
      && member.groupIds.includes('workspace_admin')
    ))
  }

  function hasWorkspaceOwnerAfterMemberRemoval(membershipId: string) {
    return data.workspaceAdmin.members.some((member) => (
      member.status === 'active'
      && member.membershipId !== membershipId
      && member.groupIds.includes('workspace_owner')
    ))
  }

  function getFinding(findingId: string): Finding | undefined {
    if (data.findingDetails[findingId]) {
      return data.findingDetails[findingId]
    }

    if (data.findingDetail.findingId === findingId) {
      return data.findingDetail
    }

    return data.findings.find((finding) => finding.findingId === findingId)
  }

  function isGoogleDriveSource(sourceId: string): boolean {
    return data.sources.some((source) => source.sourceId === sourceId && source.sourceType === 'google_drive_selection')
  }

  function getReviewSupport(findingId: string) {
    const finding = getFinding(findingId)
    const actorId = data.workspaceAdmin.currentMembership?.accountId ?? data.permissionBoundary.actorId
    const cachedReviewSupport = reviewSupportByFindingId[findingId]

    if (cachedReviewSupport?.actorId === actorId) {
      return cachedReviewSupport
    }

    if (!finding) {
      return data.reviewSupport
    }

    if (data.reviewSupport.findingId === findingId && data.reviewSupport.actorId === actorId) {
      return data.reviewSupport
    }

    return buildReviewSupport({
      actorId,
      finding,
      governanceConfig: data.governanceConfig,
      occurredAt: data.meta.generatedAt,
      workspaceMembers: data.workspaceAdmin.currentMembership ? data.workspaceAdmin.members : undefined,
    })
  }

  async function loadReviewSupport(findingId: string): Promise<ReviewSupport> {
    if (serverAvailable.current) {
      try {
        const result = await getServerReviewSupport(findingId)
        setReviewSupportByFindingId((current) => ({ ...current, [findingId]: result.data }))
        return result.data
      } catch (error) {
        if (!shouldUseLocalFallback(error)) {
          notifyApiRejection(error, 'Review support was rejected by the project server.')
          return getReviewSupport(findingId)
        }
        markServerUnavailable()
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local review support.')
      }
    }

    const reviewSupport = getReviewSupport(findingId)
    setReviewSupportByFindingId((current) => ({ ...current, [findingId]: reviewSupport }))
    return reviewSupport
  }

  return (
    <DataContext.Provider
      value={{
        sources: data.sources,
        scan: data.scan,
        findings: data.findings,
        auditEvents: data.auditEvents,
        metrics: data.metrics,
        evaluation: data.evaluation,
        governanceConfig: data.governanceConfig,
        permissionBoundary: data.permissionBoundary,
        reviewSupport: data.reviewSupport,
        workspaceDirectory: data.workspaceDirectory,
        workspaceAdmin: data.workspaceAdmin,
        meta: data.meta,
        serverConnection,
        runtimeAuthorizedSourceIds,
        notifications,
        getFinding,
        getReviewSupport,
        loadReviewSupport,
        createSource,
        updateSource,
        deleteSource,
        startScan,
        testSourceConnection,
        reviewFinding,
        createWorkspace,
        switchWorkspace,
        updateWorkspaceSettings,
        createWorkspaceInvitation,
        acceptWorkspaceInvitation,
        createWorkspaceGroup,
        updateWorkspaceGroup,
        deleteWorkspaceGroup,
        updateWorkspaceMember,
        deleteWorkspaceMember,
        transferWorkspaceOwner,
        deleteWorkspace,
        dismissNotification: (notificationId) => setNotifications((current) => current.filter(({ id }) => id !== notificationId)),
        clearNotifications: () => setNotifications([]),
      }}
    >
      {children}
    </DataContext.Provider>
  )

  async function refreshServerData(successNotification: string) {
    const nextData = await loadServerData(localMocksEnabled ? getInitialMockData() : getEmptyData())
    markServerConnected()
    setData(nextData)
    setReviewSupportByFindingId(nextData.reviewSupport.findingId ? { [nextData.reviewSupport.findingId]: nextData.reviewSupport } : {})
    notify(successNotification)
  }
}
