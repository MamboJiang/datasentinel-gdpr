import type {
  ContentExtractionSummary,
  FileInventoryFamily,
  FileInventorySummary,
  GovernanceConfig,
  SignalDetectionSummary,
  SignalTypeCount,
} from '../types'
import { findingTemplates } from './findingTemplates'

type SignalDetectionState = 'pending' | 'completed'

const contextByFamily: Record<string, string> = {
  Expense_Report: 'expense_report',
  IT_Access_Request: 'it_access',
  Incident_Report: 'incident_report',
  Source_Documents: 'source_documents',
  Supplier_Onboarding: 'supplier_onboarding',
  Training_Evaluation: 'training_evaluation',
}

export function buildSignalDetectionSummary(
  inventory: FileInventorySummary,
  extraction: ContentExtractionSummary,
  governanceConfig: GovernanceConfig,
  state: SignalDetectionState,
): SignalDetectionSummary {
  const signalTypeCounts = state === 'completed'
    ? buildSignalTypeCounts(inventory.sampleFamilies, governanceConfig)
    : []
  const detectedSignals = signalTypeCounts.reduce((total, signalType) => total + signalType.signals, 0)
  const findingsWithSignals = state === 'completed'
    ? inventory.sampleFamilies.reduce((total, family) => total + (family.flaggedFiles ?? 0), 0)
    : 0

  return {
    status: state,
    detectorRulesVersion: 'deterministic-p0-v1',
    detectorRulesHash: `sha256:${governanceConfig.activePolicyPack.version}_${extraction.extractionFingerprint}_signal_detection_${state}`,
    evidenceRequirements: governanceConfig.activePolicyPack.evidenceRequirements ?? [],
    evaluatedEvidenceCandidates: state === 'completed' ? extraction.redactedEvidenceCandidates : 0,
    detectedSignals,
    redactedSignals: detectedSignals,
    findingsWithSignals,
    rawContentExposed: false,
    signalTypeCounts,
    warnings: buildWarnings(state, extraction, detectedSignals),
  }
}

function buildSignalTypeCounts(
  families: FileInventoryFamily[],
  governanceConfig: GovernanceConfig,
): SignalTypeCount[] {
  const counts = new Map<string, number>()

  for (const family of families) {
    const contextCategory = contextByFamily[family.family] ?? 'unknown'
    const template = findingTemplates[contextCategory]
    const flaggedFiles = family.flaggedFiles ?? 0

    if (!template || flaggedFiles <= 0) {
      continue
    }

    for (const signal of template.signals) {
      counts.set(signal.type, (counts.get(signal.type) ?? 0) + flaggedFiles)
    }
  }

  return Array.from(counts.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([type, signals]) => ({
      type,
      signals,
      evidenceRequirement: findEvidenceRequirement(type, governanceConfig),
    }))
}

function findEvidenceRequirement(type: string, governanceConfig: GovernanceConfig): string | undefined {
  const policyMentionsType = governanceConfig.activePolicyPack.riskGuidance?.some((guidance) => (
    guidance.signalTypes?.includes(type)
  ))

  return policyMentionsType ? 'detector_signal' : undefined
}

function buildWarnings(
  state: SignalDetectionState,
  extraction: ContentExtractionSummary,
  detectedSignals: number,
): string[] {
  if (state === 'pending') {
    return ['Signal detection waits for completed content extraction.']
  }

  const warnings: string[] = []

  if (extraction.rawContentExposed) {
    warnings.push('Signal detection cannot publish evidence while raw-content exposure is true.')
  }

  if (detectedSignals === 0 && extraction.redactedEvidenceCandidates > 0) {
    warnings.push('Evidence candidates were extracted but no deterministic signal matched.')
  }

  return warnings
}
