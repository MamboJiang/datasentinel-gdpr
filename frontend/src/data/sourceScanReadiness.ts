import type { GovernanceConfig, Source } from '../types'
import { isSourceScanReady } from './scanProfiles'

export function requiresRuntimeAuthorization(source: Source): boolean {
  return source.sourceType === 'google_drive_selection'
}

export function canStartSourceScan(source: Source, governanceConfig: GovernanceConfig, runtimeAuthorizedSourceIds: string[]): boolean {
  if (requiresRuntimeAuthorization(source)) {
    return hasConnectedAdapter(source, governanceConfig) && runtimeAuthorizedSourceIds.includes(source.sourceId)
  }

  if (!isSourceScanReady(source, governanceConfig)) {
    return false
  }

  return true
}

export function sourceScanBlockReason(source: Source, governanceConfig: GovernanceConfig, runtimeAuthorizedSourceIds: string[]): string | undefined {
  if (requiresRuntimeAuthorization(source) && !runtimeAuthorizedSourceIds.includes(source.sourceId)) {
    return 'Google Drive scan requires reconnecting through the Picker'
  }

  if (!canStartSourceScan(source, governanceConfig, runtimeAuthorizedSourceIds)) {
    return 'Scan requires a connected source'
  }

  return undefined
}

function hasConnectedAdapter(source: Source, governanceConfig: GovernanceConfig): boolean {
  return governanceConfig.sourceAdapters.some((candidate) => (
    candidate.sourceType === source.sourceType && candidate.status === 'connected'
  ))
}
