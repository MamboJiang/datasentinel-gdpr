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
  toast: string | null
  getFinding: (findingId: string) => Finding | undefined
  startScan: (scanType: 'full' | 'delta') => void
  reviewFinding: (input: ReviewInput) => void
  clearToast: () => void
}

export const DataContext = createContext<DataContextValue | null>(null)
