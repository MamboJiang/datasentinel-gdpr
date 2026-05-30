import type { FileInventoryFamily, FileInventorySummary, Source } from '../types'

export type InventoryProfile = {
  flaggedFiles: number
  scannedFiles: number
  scanId: string
  totalBytes: number
  totalFiles: number
}

type InventoryState = 'running' | 'completed'

const organizerFamilyWeights: Record<string, number> = {
  Expense_Report: 9,
  IT_Access_Request: 8,
  Incident_Report: 7,
  Supplier_Onboarding: 10,
  Training_Evaluation: 8,
}

export function buildFileInventorySummary(source: Source, profile: InventoryProfile, state: InventoryState): FileInventorySummary {
  const fingerprintedFiles = state === 'completed' ? profile.totalFiles : profile.scannedFiles
  const skippedFiles = state === 'completed' ? 0 : Math.max(0, profile.totalFiles - fingerprintedFiles)

  return {
    status: state,
    sourceSnapshotId: `snapshot_${source.sourceId}_${profile.scanId}`,
    inventoryFingerprint: `sha256:${profile.scanId}_inventory_${state}`,
    totalCandidateFiles: profile.totalFiles,
    fingerprintedFiles,
    skippedFiles,
    totalBytes: profile.totalBytes,
    permissionSnapshots: fingerprintedFiles,
    sampleFamilies: buildFamilySummaries(source, profile, fingerprintedFiles),
    warnings: state === 'running'
      ? ['Inventory is partial while the scan is running.']
      : [],
  }
}

function buildFamilySummaries(source: Source, profile: InventoryProfile, fingerprintedFiles: number): FileInventoryFamily[] {
  const families = source.sampleFamilies?.length ? source.sampleFamilies : ['Source_Documents']
  const totalWeight = families.reduce((total, family) => total + (organizerFamilyWeights[family] ?? 1), 0)

  return families.map((family) => {
    const weight = organizerFamilyWeights[family] ?? 1
    const candidateFiles = Math.max(1, Math.round((profile.totalFiles * weight) / totalWeight))
    const processedRatio = profile.totalFiles > 0 ? fingerprintedFiles / profile.totalFiles : 0

    return {
      family,
      candidateFiles,
      flaggedFiles: Math.round((profile.flaggedFiles * weight) / totalWeight),
      bytes: Math.round((profile.totalBytes * weight) / totalWeight),
      processedFiles: Math.min(candidateFiles, Math.round(candidateFiles * processedRatio)),
    }
  })
}
