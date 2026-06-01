import type { Finding } from '../types'
import type { MockData } from './mockApi'
import { isApiRequestError } from './serverApi'

export type ServerRefreshOptions = {
  notifyOnScanCompletion?: boolean
  successNotification?: string
}

export function shouldUseLocalFallback(error: unknown): boolean {
  return !isApiRequestError(error)
}

export function canUseLocalFallback(error: unknown, localMocksEnabled: boolean): boolean {
  return localMocksEnabled && shouldUseLocalFallback(error)
}

export function findFindingInData(current: MockData, findingId: string): Finding | undefined {
  if (current.findingDetails[findingId]) {
    return current.findingDetails[findingId]
  }

  if (current.findingDetail.findingId === findingId) {
    return current.findingDetail
  }

  return current.findings.find((finding) => finding.findingId === findingId)
}

export function mergeVisibleFindingDetails(previous: MockData, next: MockData): Record<string, Finding> {
  const visibleFindingIds = new Set(next.findings.map((finding) => finding.findingId))

  if (next.findingDetail.findingId) {
    visibleFindingIds.add(next.findingDetail.findingId)
  }

  return {
    ...Object.fromEntries(
      Object.entries(previous.findingDetails).filter(([findingId]) => visibleFindingIds.has(findingId)),
    ),
    ...next.findingDetails,
  }
}

export function scanCompletionMessage(scan: MockData['scan']): string {
  return `${scan.scanType === 'delta' ? 'Delta' : 'Full'} scan completed.`
}

export function isScanCompletionTransition(previousScan: MockData['scan'], nextScan: MockData['scan']): boolean {
  return (
    previousScan.scanId === nextScan.scanId
    && previousScan.status === 'running'
    && nextScan.status === 'completed'
  )
}
