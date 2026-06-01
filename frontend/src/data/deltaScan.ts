import type { DeltaScanSummary, Scan } from '../types'
import type { ScanProfile } from './scanProfiles'

type DeltaScanState = 'running' | 'completed'

type DeltaBaseline = {
  baselineScanId: string
  baselineSourceSnapshotId: string
  baselineInventoryFingerprint: string
  baselineTotalFiles: number
  baselineFindingCount: number
}

type DeltaScanSummaryInput = {
  baseline: DeltaBaseline
  profile: ScanProfile
  state: DeltaScanState
}

const deltaChangeProfile = {
  missingFiles: 1,
  modifiedFiles: 4,
  newFiles: 2,
}

export function getDeltaScanBaseline(scan: Scan, sourceId: string): DeltaBaseline | null {
  if (scan.status !== 'completed' || scan.sourceId !== sourceId) {
    return null
  }

  if (scan.scanType === 'full') {
    return {
      baselineScanId: scan.scanId,
      baselineSourceSnapshotId: scan.fileInventory?.sourceSnapshotId ?? `${scan.scanId}_snapshot_unknown`,
      baselineInventoryFingerprint: scan.fileInventory?.inventoryFingerprint ?? `${scan.scanId}_inventory_unknown`,
      baselineTotalFiles: scan.totalFiles ?? scan.fileInventory?.totalCandidateFiles ?? 0,
      baselineFindingCount: scan.findingAssembly?.assembledFindings ?? scan.flaggedFiles ?? 0,
    }
  }

  if (scan.scanType === 'delta' && scan.deltaScan) {
    return toDeltaBaseline(scan.deltaScan)
  }

  return null
}

export function canStartDeltaScan(scan: Scan, sourceId: string): boolean {
  return Boolean(getDeltaScanBaseline(scan, sourceId))
}

export function buildDeltaScanSummary(input: DeltaScanSummaryInput): DeltaScanSummary {
  const changedFiles = input.profile.totalFiles
  const processedChangedFiles = input.state === 'completed'
    ? changedFiles
    : Math.min(input.profile.scannedFiles, changedFiles)
  const unchangedFiles = Math.max(
    0,
    input.baseline.baselineTotalFiles - changedFiles - deltaChangeProfile.missingFiles,
  )
  const reopenedFindings = input.state === 'completed' ? input.profile.completedFlaggedFiles : 0

  return {
    status: input.state,
    baselineScanId: input.baseline.baselineScanId,
    baselineSourceSnapshotId: input.baseline.baselineSourceSnapshotId,
    baselineInventoryFingerprint: input.baseline.baselineInventoryFingerprint,
    baselineTotalFiles: input.baseline.baselineTotalFiles,
    baselineFindingCount: input.baseline.baselineFindingCount,
    deltaFingerprint: `sha256:${input.baseline.baselineInventoryFingerprint}_${input.profile.scanId}_delta_${input.state}`,
    changedFiles,
    newFiles: deltaChangeProfile.newFiles,
    modifiedFiles: deltaChangeProfile.modifiedFiles,
    unchangedFiles,
    missingFiles: deltaChangeProfile.missingFiles,
    processedChangedFiles,
    carriedForwardFiles: unchangedFiles,
    reopenedFindings,
    unchangedFindingsCarriedForward: Math.max(0, input.baseline.baselineFindingCount - reopenedFindings),
    missingFilesTreatedAsDeleted: false,
    rawContentExposed: false,
    legalConclusionProvided: false,
    deletionExecuted: false,
    warnings: buildDeltaWarnings(input.state, unchangedFiles),
  }
}

export function completeDeltaScanSummary(scan: Scan, profile: ScanProfile): DeltaScanSummary | undefined {
  return scan.scanType === 'delta' && scan.deltaScan
    ? buildDeltaScanSummary({ baseline: toDeltaBaseline(scan.deltaScan), profile, state: 'completed' })
    : undefined
}

function toDeltaBaseline(deltaScan: DeltaScanSummary): DeltaBaseline {
  return {
    baselineScanId: deltaScan.baselineScanId,
    baselineSourceSnapshotId: deltaScan.baselineSourceSnapshotId,
    baselineInventoryFingerprint: deltaScan.baselineInventoryFingerprint,
    baselineTotalFiles: deltaScan.baselineTotalFiles,
    baselineFindingCount: deltaScan.baselineFindingCount,
  }
}

function buildDeltaWarnings(state: DeltaScanState, unchangedFiles: number): string[] {
  const warnings = state === 'running'
    ? ['Delta comparison is partial while the changed-file scan is running.']
    : []

  if (unchangedFiles > 0) {
    warnings.push(`${unchangedFiles} unchanged baseline files are carried forward without being rescanned.`)
  }

  warnings.push('Missing baseline files are represented as source inventory changes, not lawdit deletion.')

  return warnings
}
