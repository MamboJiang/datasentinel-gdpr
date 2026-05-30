import type { ContentExtractionSummary, FileInventorySummary } from '../types'

type ExtractionState = 'running' | 'completed'

type ExtractionProfile = {
  completedEvidenceCandidates: number
  completedSuccessfulFiles: number
  completedUnsupportedFiles: number
  completedWarningFiles: number
  runningEvidenceCandidates: number
  runningSuccessfulFiles: number
  runningUnsupportedFiles: number
  runningWarningFiles: number
}

const profiles: Record<string, ExtractionProfile> = {
  full: {
    completedEvidenceCandidates: 64,
    completedSuccessfulFiles: 38,
    completedUnsupportedFiles: 2,
    completedWarningFiles: 4,
    runningEvidenceCandidates: 21,
    runningSuccessfulFiles: 12,
    runningUnsupportedFiles: 1,
    runningWarningFiles: 2,
  },
  delta: {
    completedEvidenceCandidates: 10,
    completedSuccessfulFiles: 5,
    completedUnsupportedFiles: 0,
    completedWarningFiles: 1,
    runningEvidenceCandidates: 8,
    runningSuccessfulFiles: 3,
    runningUnsupportedFiles: 0,
    runningWarningFiles: 1,
  },
}

export function buildContentExtractionSummary(
  scanType: string,
  inventory: FileInventorySummary,
  state: ExtractionState,
): ContentExtractionSummary {
  const profile = profiles[scanType === 'delta' ? 'delta' : 'full']
  const processedFiles = state === 'completed' ? inventory.totalCandidateFiles : inventory.fingerprintedFiles
  const successfulFiles = state === 'completed' ? profile.completedSuccessfulFiles : profile.runningSuccessfulFiles
  const warningFiles = state === 'completed' ? profile.completedWarningFiles : profile.runningWarningFiles
  const unsupportedFiles = state === 'completed' ? profile.completedUnsupportedFiles : profile.runningUnsupportedFiles
  const redactedEvidenceCandidates = state === 'completed'
    ? profile.completedEvidenceCandidates
    : profile.runningEvidenceCandidates
  const ocrDeferredFiles = state === 'completed' ? Math.min(2, warningFiles) : Math.min(1, warningFiles)

  return {
    status: state,
    extractionFingerprint: `sha256:${inventory.sourceSnapshotId}_extraction_${state}`,
    processedFiles,
    successfulFiles,
    warningFiles,
    unsupportedFiles,
    ocrDeferredFiles,
    redactedEvidenceCandidates,
    rawContentExposed: false,
    methods: [
      { method: 'metadata', files: processedFiles, status: state },
      { method: 'text_layer', files: successfulFiles, status: state },
      { method: 'structured_table', files: Math.round(successfulFiles * 0.24), status: state },
      { method: 'ocr_deferred', files: ocrDeferredFiles, status: warningFiles > 0 ? 'warning' : state },
    ],
    warnings: buildWarnings(state, warningFiles, unsupportedFiles, ocrDeferredFiles),
  }
}

function buildWarnings(
  state: ExtractionState,
  warningFiles: number,
  unsupportedFiles: number,
  ocrDeferredFiles: number,
): string[] {
  const warnings = state === 'running'
    ? ['Extraction is partial while the scan is running.']
    : []

  if (warningFiles > 0) {
    warnings.push(`${warningFiles} files need recoverable extraction review.`)
  }

  if (unsupportedFiles > 0) {
    warnings.push(`${unsupportedFiles} files use unsupported formats in this P0 fixture.`)
  }

  if (ocrDeferredFiles > 0) {
    warnings.push(`${ocrDeferredFiles} files are marked for future OCR instead of paid P0 processing.`)
  }

  return warnings
}
