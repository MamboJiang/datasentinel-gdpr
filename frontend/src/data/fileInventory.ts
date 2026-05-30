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
  const candidateFilesByFamily = allocateCounts(profile.totalFiles, families, true)
  const flaggedFilesByFamily = allocateCounts(profile.flaggedFiles, families, false)
  const totalWeight = totalFamilyWeight(families)

  return families.map((family, index) => {
    const weight = organizerFamilyWeights[family] ?? 1
    const candidateFiles = candidateFilesByFamily[index] ?? 0
    const processedRatio = profile.totalFiles > 0 ? fingerprintedFiles / profile.totalFiles : 0

    return {
      family,
      candidateFiles,
      flaggedFiles: flaggedFilesByFamily[index] ?? 0,
      bytes: Math.round((profile.totalBytes * weight) / totalWeight),
      processedFiles: Math.min(candidateFiles, Math.round(candidateFiles * processedRatio)),
    }
  })
}

function allocateCounts(total: number, families: string[], minimumOne: boolean): number[] {
  if (total <= 0 || families.length === 0) {
    return families.map(() => 0)
  }

  const totalWeight = totalFamilyWeight(families)
  const shares = families.map((family, index) => {
    const exact = (total * (organizerFamilyWeights[family] ?? 1)) / totalWeight

    return {
      index,
      floor: Math.floor(exact),
      remainder: exact - Math.floor(exact),
    }
  })
  const minimum = minimumOne && total >= families.length ? 1 : 0
  const counts = shares.map((share) => Math.max(minimum, share.floor))
  let remaining = total - counts.reduce((sum, count) => sum + count, 0)

  for (const share of [...shares].sort((left, right) => right.remainder - left.remainder)) {
    if (remaining <= 0) {
      break
    }

    counts[share.index] += 1
    remaining -= 1
  }

  return counts
}

function totalFamilyWeight(families: string[]): number {
  return families.reduce((total, family) => total + (organizerFamilyWeights[family] ?? 1), 0)
}
