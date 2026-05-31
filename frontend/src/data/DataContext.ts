import { createContext } from 'react'
import type {
  AdminMetrics,
  AuditEvent,
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
} from '../types'
import type { StartScanOptions } from './scanWorkflow'
import type { CreateSourceInput } from './serverApi'

export type AppNotification = {
  id: string
  message: string
  createdAt: string
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
  meta: Meta
  notifications: AppNotification[]
  getFinding: (findingId: string) => Finding | undefined
  getReviewSupport: (findingId: string) => ReviewSupport
  createSource: (input: CreateSourceInput) => void
  deleteSource: (sourceId: string) => void
  startScan: (options: StartScanOptions) => void
  testSourceConnection: (sourceId: string) => void
  reviewFinding: (input: ReviewInput) => void
  dismissNotification: (notificationId: string) => void
  clearNotifications: () => void
}

export const DataContext = createContext<DataContextValue | null>(null)
