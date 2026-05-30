import type {
  ContentExtractionSummary,
  ContextCategorySummary,
  ContextRiskSummary,
  FileInventoryFamily,
  FileInventorySummary,
  GovernanceConfig,
} from '../types'

type ContextRiskState = 'pending' | 'completed'

type RiskProfile = {
  highRiskFindings: number
  lowRiskFindings: number
  mediumRiskFindings: number
  retentionReviewFiles: number
}

const contextByFamily: Record<string, string> = {
  Expense_Report: 'expense_report',
  IT_Access_Request: 'it_access',
  Incident_Report: 'incident_report',
  Source_Documents: 'source_documents',
  Supplier_Onboarding: 'supplier_onboarding',
  Training_Evaluation: 'training_evaluation',
}

const riskProfiles: Record<string, RiskProfile> = {
  full: {
    highRiskFindings: 5,
    mediumRiskFindings: 9,
    lowRiskFindings: 3,
    retentionReviewFiles: 7,
  },
  delta: {
    highRiskFindings: 1,
    mediumRiskFindings: 1,
    lowRiskFindings: 0,
    retentionReviewFiles: 1,
  },
}

export function buildContextRiskSummary(
  scanType: string,
  inventory: FileInventorySummary,
  extraction: ContentExtractionSummary,
  governanceConfig: GovernanceConfig,
  state: ContextRiskState,
): ContextRiskSummary {
  const policyPackVersion = governanceConfig.activePolicyPack.version
  const status = state
  const contextCategories = state === 'completed'
    ? buildContextCategories(inventory.sampleFamilies, extraction.redactedEvidenceCandidates, governanceConfig)
    : []
  const profile = state === 'completed' ? getRiskProfile(scanType) : emptyRiskProfile()
  const riskAssessedFindings = profile.highRiskFindings + profile.mediumRiskFindings + profile.lowRiskFindings

  return {
    status,
    policyPackVersion,
    riskRulesFingerprint: `sha256:${policyPackVersion}_${extraction.extractionFingerprint}_context_risk_${state}`,
    assessedEvidenceCandidates: state === 'completed' ? extraction.redactedEvidenceCandidates : 0,
    contextClassifiedFindings: riskAssessedFindings,
    riskAssessedFindings,
    highRiskFindings: profile.highRiskFindings,
    mediumRiskFindings: profile.mediumRiskFindings,
    lowRiskFindings: profile.lowRiskFindings,
    retentionReviewFiles: profile.retentionReviewFiles,
    humanReviewRequiredFindings: riskAssessedFindings,
    legalConclusionProvided: false,
    contextCategories,
    warnings: buildWarnings(state, contextCategories),
  }
}

function buildContextCategories(
  families: FileInventoryFamily[],
  evidenceCandidates: number,
  governanceConfig: GovernanceConfig,
): ContextCategorySummary[] {
  const totalFlaggedFiles = families.reduce((total, family) => total + (family.flaggedFiles ?? 0), 0)
  let remainingEvidence = evidenceCandidates

  return families.map((family, index) => {
    const contextCategory = contextByFamily[family.family] ?? 'unknown'
    const flaggedFiles = family.flaggedFiles ?? 0
    const evidenceShare = index === families.length - 1
      ? remainingEvidence
      : calculateEvidenceShare(evidenceCandidates, flaggedFiles, totalFlaggedFiles)

    remainingEvidence = Math.max(0, remainingEvidence - evidenceShare)

    return {
      contextCategory,
      sourceFamily: family.family,
      flaggedFiles,
      evidenceCandidates: evidenceShare,
      riskGuidance: findRiskGuidance(contextCategory, governanceConfig),
      retentionRuleApplied: hasRetentionRule(contextCategory, governanceConfig),
    }
  })
}

function calculateEvidenceShare(totalEvidence: number, flaggedFiles: number, totalFlaggedFiles: number): number {
  if (totalEvidence <= 0 || flaggedFiles <= 0 || totalFlaggedFiles <= 0) {
    return 0
  }

  return Math.max(1, Math.round((totalEvidence * flaggedFiles) / totalFlaggedFiles))
}

function findRiskGuidance(contextCategory: string, governanceConfig: GovernanceConfig): string | undefined {
  const guidance = governanceConfig.activePolicyPack.riskGuidance?.find((candidate) => (
    candidate.contextCategory === contextCategory
  ))

  return guidance?.reviewReason
}

function hasRetentionRule(contextCategory: string, governanceConfig: GovernanceConfig): boolean {
  return Boolean(governanceConfig.activePolicyPack.retentionRules?.some((rule) => (
    rule.documentCategory === contextCategory
  )))
}

function buildWarnings(state: ContextRiskState, contextCategories: ContextCategorySummary[]): string[] {
  if (state === 'pending') {
    return ['Context/risk judgment waits for completed signal detection.']
  }

  const unknownGuidanceCount = contextCategories.filter((category) => !category.riskGuidance).length

  return unknownGuidanceCount > 0
    ? [`${unknownGuidanceCount} context categories use neutral risk guidance in this P0 fixture.`]
    : []
}

function getRiskProfile(scanType: string): RiskProfile {
  return riskProfiles[scanType === 'delta' ? 'delta' : 'full']
}

function emptyRiskProfile(): RiskProfile {
  return {
    highRiskFindings: 0,
    mediumRiskFindings: 0,
    lowRiskFindings: 0,
    retentionReviewFiles: 0,
  }
}
