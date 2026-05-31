import { createContext } from 'react'
import type {
  AdminMetrics,
  AuditEvent,
  CreateWorkspaceInvitationInput,
  CreateWorkspaceInput,
  DeleteWorkspaceGroupInput,
  DeleteWorkspaceInput,
  DeleteWorkspaceMemberInput,
  EvaluationSummary,
  Finding,
  FindingSummary,
  Meta,
  GovernanceConfig,
  PermissionBoundary,
  ReviewInput,
  ReviewSupport,
  Scan,
  Source,
  WorkspaceAdminSummary,
  WorkspaceDirectory,
  WorkspaceGroup,
  WorkspaceGroupInput,
  WorkspaceInvitation,
  UpdateWorkspaceGroupInput,
  UpdateWorkspaceMemberInput,
  TransferWorkspaceOwnerInput,
} from '../types'
import type { StartScanOptions } from './scanWorkflow'
import type { CreateSourceInput } from './serverApi'

export type AppNotification = {
  id: string
  message: string
  createdAt: string
}

export type ServerConnectionStatus = 'checking' | 'connected' | 'disconnected'

export type ServerConnection = {
  checkedAt: string | null
  message: string
  status: ServerConnectionStatus
}

export type DataContextValue = {
  sources: Source[]
  scan: Scan
  findings: FindingSummary[]
  auditEvents: AuditEvent[]
  metrics: AdminMetrics
  evaluation: EvaluationSummary
  governanceConfig: GovernanceConfig
  permissionBoundary: PermissionBoundary
  reviewSupport: ReviewSupport
  workspaceDirectory: WorkspaceDirectory
  workspaceAdmin: WorkspaceAdminSummary
  meta: Meta
  serverConnection: ServerConnection
  runtimeAuthorizedSourceIds: string[]
  notifications: AppNotification[]
  getFinding: (findingId: string) => Finding | undefined
  getReviewSupport: (findingId: string) => ReviewSupport
  createSource: (input: CreateSourceInput) => void
  deleteSource: (sourceId: string) => void
  startScan: (options: StartScanOptions) => void
  testSourceConnection: (sourceId: string) => void
  reviewFinding: (input: ReviewInput) => void
  createWorkspace: (input: CreateWorkspaceInput) => void
  switchWorkspace: (workspaceId: string) => Promise<boolean>
  createWorkspaceInvitation: (input: CreateWorkspaceInvitationInput) => Promise<WorkspaceInvitation | null>
  acceptWorkspaceInvitation: (invitationId: string) => Promise<boolean>
  createWorkspaceGroup: (input: WorkspaceGroupInput) => Promise<WorkspaceGroup | null>
  updateWorkspaceGroup: (input: UpdateWorkspaceGroupInput) => Promise<WorkspaceGroup | null>
  deleteWorkspaceGroup: (input: DeleteWorkspaceGroupInput) => Promise<boolean>
  updateWorkspaceMember: (input: UpdateWorkspaceMemberInput) => Promise<boolean>
  deleteWorkspaceMember: (input: DeleteWorkspaceMemberInput) => Promise<boolean>
  transferWorkspaceOwner: (input: TransferWorkspaceOwnerInput) => Promise<boolean>
  deleteWorkspace: (input: DeleteWorkspaceInput) => Promise<boolean>
  dismissNotification: (notificationId: string) => void
  clearNotifications: () => void
}

export const DataContext = createContext<DataContextValue | null>(null)
