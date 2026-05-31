import type { GovernanceConfig, Source } from '../types'
import { isSourceScanReady } from './scanProfiles'

export function requiresRuntimeAuthorization(source: Source): boolean {
  return source.sourceType === 'google_drive_selection'
}

export function sourceDisplayStatus(source: Source, runtimeAuthorizedSourceIds: string[], googleDriveBindingConnected = false): string {
  if (requiresRuntimeAuthorization(source) && hasGoogleDriveAuthorization(runtimeAuthorizedSourceIds, source.sourceId, googleDriveBindingConnected)) {
    return 'connected'
  }

  return source.status
}

export function canStartSourceScan(source: Source, governanceConfig: GovernanceConfig, runtimeAuthorizedSourceIds: string[], googleDriveBindingConnected = false): boolean {
  if (requiresRuntimeAuthorization(source)) {
    return hasConnectedAdapter(source, governanceConfig) && hasGoogleDriveAuthorization(runtimeAuthorizedSourceIds, source.sourceId, googleDriveBindingConnected)
  }

  if (!isSourceScanReady(source, governanceConfig)) {
    return false
  }

  return true
}

export function sourceScanBlockReason(source: Source, governanceConfig: GovernanceConfig, runtimeAuthorizedSourceIds: string[], googleDriveBindingConnected = false): string | undefined {
  if (requiresRuntimeAuthorization(source) && !hasGoogleDriveAuthorization(runtimeAuthorizedSourceIds, source.sourceId, googleDriveBindingConnected)) {
    return 'Google Drive scan requires a connected account binding or Picker authorization'
  }

  if (!canStartSourceScan(source, governanceConfig, runtimeAuthorizedSourceIds, googleDriveBindingConnected)) {
    return 'Scan requires a connected source'
  }

  return undefined
}

function hasConnectedAdapter(source: Source, governanceConfig: GovernanceConfig): boolean {
  return governanceConfig.sourceAdapters.some((candidate) => (
    candidate.sourceType === source.sourceType && candidate.status === 'connected'
  ))
}

function hasGoogleDriveAuthorization(runtimeAuthorizedSourceIds: string[], sourceId: string, googleDriveBindingConnected: boolean): boolean {
  return googleDriveBindingConnected || runtimeAuthorizedSourceIds.includes(sourceId)
}
