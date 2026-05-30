import type { MockData } from './mockApi'
import type { StartScanOptions } from './scanProfiles'

export type StartScanInput = StartScanOptions & {
  actorId: string
  auditEventId: string
  occurredAt: string
}

export type CompleteScanInput = {
  auditEventId: string
  occurredAt: string
  scanId: string
}

type StartScanAccepted = {
  accepted: true
  completionDelayMs: number
  data: MockData
  scanId: string
  toast: string
}

type StartScanRejected = {
  accepted: false
  data: MockData
  toast: string
}

export type StartScanResult = StartScanAccepted | StartScanRejected
