import type { GovernanceConfig, Source } from '../types'

export type ScanType = 'full' | 'delta'

export type StartScanOptions = {
  baselineScanId?: string | null
  modifiedSince?: string | null
  scanType: ScanType
  sourceId?: string
}

export type ScanProfile = {
  completionDelayMs: number
  completedFlaggedFiles: number
  durationMs: number
  flaggedFiles: number
  progress: number
  scannedFiles: number
  scanId: string
  scanType: ScanType
  throughputFilesPerSecond: number
  totalBytes: number
  totalFiles: number
}

export const scanProfiles: Record<ScanType, ScanProfile> = {
  full: {
    completionDelayMs: 2200,
    completedFlaggedFiles: 17,
    durationMs: 38200,
    flaggedFiles: 5,
    progress: 0.34,
    scannedFiles: 14,
    scanId: 'scan_demo_full',
    scanType: 'full',
    throughputFilesPerSecond: 1.1,
    totalBytes: 38210000,
    totalFiles: 42,
  },
  delta: {
    completionDelayMs: 1800,
    completedFlaggedFiles: 2,
    durationMs: 5200,
    flaggedFiles: 2,
    progress: 0.67,
    scannedFiles: 4,
    scanId: 'scan_demo_delta',
    scanType: 'delta',
    throughputFilesPerSecond: 1.15,
    totalBytes: 6240000,
    totalFiles: 6,
  },
}

export function isSourceScanReady(source: Source, governanceConfig: GovernanceConfig): boolean {
  const adapter = governanceConfig.sourceAdapters.find((candidate) => candidate.sourceType === source.sourceType)

  return source.status === 'mock_ready' && adapter?.status === 'mock_ready'
}

export function getDefaultFullScanSource(sources: Source[], governanceConfig: GovernanceConfig): Source | undefined {
  const organizerSource = sources.find((source) => source.sourceType === 'organizer_sample_repo')

  if (organizerSource && isSourceScanReady(organizerSource, governanceConfig)) {
    return organizerSource
  }

  return sources.find((source) => isSourceScanReady(source, governanceConfig))
}
