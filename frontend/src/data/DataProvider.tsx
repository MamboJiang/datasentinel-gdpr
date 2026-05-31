import { useEffect, useRef, useState, type ReactNode } from 'react'
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
  buildLocalWorkspaceGroup,
} from './workspaceLocalState'
import {
  acceptServerWorkspaceInvitation,
  createServerWorkspaceGroup,
  createServerSource,
  createServerWorkspace,
  createServerWorkspaceInvitation,
  deleteServerWorkspaceGroup,
  deleteServerSource,
  loadServerData,
  reviewServerFinding,
  startServerScan,
  testServerSourceConnection,
  updateServerWorkspaceGroup,
  type CreateSourceInput,
} from './serverApi'
import type {
  CreateWorkspaceInvitationInput,
  CreateWorkspaceInput,
  DeleteWorkspaceGroupInput,
  Finding,
  ReviewInput,
  UpdateWorkspaceGroupInput,
  WorkspaceGroup,
  WorkspaceGroupInput,
  WorkspaceInvitation,
} from '../types'

const localMocksEnabled = import.meta.env.VITE_DATASENTINEL_ENABLE_LOCAL_MOCKS === 'true'

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState(localMocksEnabled ? getInitialMockData : getEmptyData)
  const [notifications, setNotifications] = useState<DataContextValue['notifications']>([])
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

  useEffect(() => {
    let active = true
    const fallback = localMocksEnabled ? getInitialMockData() : getEmptyData()

    loadServerData(fallback)
      .then((serverData) => {
        if (!active) {
          return
        }

        serverAvailable.current = true
        setData(serverData)
      })
      .catch(() => {
        serverAvailable.current = false
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
  }, [])

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
        serverAvailable.current = false
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
        serverAvailable.current = false
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
      if (input.googleDriveAccessToken) {
        googleDriveAccessTokens.current[input.sourceId] = input.googleDriveAccessToken
      }
      const result = await createServerSource(input)
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

  async function deleteSource(sourceId: string) {
    if (!serverAvailable.current) {
      notify('Project server unavailable; source deletion requires the API server.')
      return
    }

    try {
      const result = await deleteServerSource(sourceId)
      delete googleDriveAccessTokens.current[sourceId]
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
        serverAvailable.current = false
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
        await refreshServerData('Workspace created. You are now a Workspace admin.')
        return
      } catch (error) {
        serverAvailable.current = false
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    setData((current) => applyLocalWorkspaceCreation(current, input))
    notify('Workspace created in local mock state. You are now a Workspace admin.')
  }

  async function createWorkspaceInvitation(input: CreateWorkspaceInvitationInput) {
    if (serverAvailable.current) {
      try {
        const result = await createServerWorkspaceInvitation(input)
        await refreshServerData('Workspace invitation link created.')
        return result.data
      } catch (error) {
        serverAvailable.current = false
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
        serverAvailable.current = false
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
        serverAvailable.current = false
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
        serverAvailable.current = false
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceGroups()) {
      notify('Workspace group management permission is required.')
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
        serverAvailable.current = false
        notify(error instanceof Error ? error.message : 'Project server unavailable; using local Workspace mock.')
      }
    }

    if (!canManageWorkspaceGroups()) {
      notify('Workspace group management permission is required.')
      return false
    }

    if (input.groupId === 'workspace_admin') {
      notify('Workspace admin group cannot be deleted.')
      return false
    }

    setData((current) => applyLocalWorkspaceGroupDeletion(current, input.workspaceId, input.groupId))
    notify('Workspace group deleted in local mock state.')
    return true
  }

  function canManageWorkspaceGroups() {
    return data.workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_groups')
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

  function getReviewSupport(findingId: string) {
    const finding = getFinding(findingId)

    if (!finding) {
      return data.reviewSupport
    }

    return buildReviewSupport({
      actorId: data.permissionBoundary.actorId,
      finding,
      governanceConfig: data.governanceConfig,
      occurredAt: data.meta.generatedAt,
    })
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
        notifications,
        getFinding,
        getReviewSupport,
        createSource,
        deleteSource,
        startScan,
        testSourceConnection,
        reviewFinding,
        createWorkspace,
        createWorkspaceInvitation,
        acceptWorkspaceInvitation,
        createWorkspaceGroup,
        updateWorkspaceGroup,
        deleteWorkspaceGroup,
        dismissNotification: (notificationId) => setNotifications((current) => current.filter(({ id }) => id !== notificationId)),
        clearNotifications: () => setNotifications([]),
      }}
    >
      {children}
    </DataContext.Provider>
  )

  async function refreshServerData(successNotification: string) {
    const nextData = await loadServerData(localMocksEnabled ? getInitialMockData() : getEmptyData())
    serverAvailable.current = true
    setData(nextData)
    notify(successNotification)
  }
}
