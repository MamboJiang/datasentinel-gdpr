import type {
  AuditEvent,
  ContentExtractionSummary,
  ContextCategorySummary,
  ContextRiskSummary,
  Finding,
  FindingAssemblySummary,
  FindingSummary,
  GovernanceConfig,
  Owner,
  OwnerAssignmentSummary,
  Scan,
  Source,
} from '../types'
import { createAuditEvent } from './auditEventRecording'
import {
  escalationOwner,
  fallbackOwner,
  findingTemplates,
  type FindingTemplate,
} from './findingTemplates'

type AssemblyState = 'pending' | 'completed'

type AssemblyInput = {
  contentExtraction: ContentExtractionSummary
  contextRisk: ContextRiskSummary
  governanceConfig: GovernanceConfig
  occurredAt: string
  ownerAssignment: OwnerAssignmentSummary
  scan: Scan
  source: Source
  state: AssemblyState
}

type AssemblyResult = {
  summary: FindingAssemblySummary
  findings: FindingSummary[]
  findingDetails: Record<string, Finding>
}

export function buildFindingAssemblySummary(input: AssemblyInput): FindingAssemblySummary {
  const completed = input.state === 'completed'
  const assembledFindings = completed ? input.ownerAssignment.assignedFindings : 0
  const evidenceSignals = completed ? countSignals(input.contextRisk.contextCategories) : 0
  const missingEvidenceCards = completed ? Math.max(0, input.ownerAssignment.assignedFindings - assembledFindings) : 0

  return {
    status: input.state,
    policyPackVersion: input.governanceConfig.activePolicyPack.version,
    sourceSnapshotId: input.scan.fileInventory?.sourceSnapshotId ?? `${input.scan.scanId}_snapshot_pending`,
    assemblyRulesFingerprint: `sha256:${input.ownerAssignment.assignmentRulesFingerprint}_${input.contentExtraction.extractionFingerprint}_finding_assembly_${input.state}`,
    assembledFindings,
    evidenceCards: assembledFindings,
    evidenceSignals,
    redactedEvidenceSnippets: evidenceSignals,
    missingEvidenceCards,
    deniedActionCount: completed ? 1 : 0,
    rawContentExposed: false,
    legalConclusionProvided: false,
    warnings: buildWarnings(input.state, input.contentExtraction, input.ownerAssignment, missingEvidenceCards),
  }
}

export function assembleFindings(input: AssemblyInput): AssemblyResult {
  const summary = buildFindingAssemblySummary(input)

  if (input.state !== 'completed') {
    return {
      summary,
      findings: [],
      findingDetails: {},
    }
  }

  const riskLevels = createRiskLevels(input.contextRisk)
  const owners = createOwners(input.ownerAssignment)
  const findings: FindingSummary[] = []
  const findingDetails: Record<string, Finding> = {}
  let findingIndex = 0

  for (const category of input.contextRisk.contextCategories) {
    const template = findingTemplates[category.contextCategory] ?? findingTemplates.incident_report

    for (let categoryIndex = 0; categoryIndex < category.flaggedFiles; categoryIndex += 1) {
      const finding = buildFinding({
        category,
        categoryIndex,
        findingIndex,
        governanceConfig: input.governanceConfig,
        occurredAt: input.occurredAt,
        owner: owners[findingIndex] ?? fallbackOwner,
        riskLevel: riskLevels[findingIndex] ?? 'medium',
        scan: input.scan,
        source: input.source,
        template,
      })

      findings.push(toSummary(finding))
      findingDetails[finding.findingId] = finding
      findingIndex += 1
    }
  }

  return {
    summary,
    findings,
    findingDetails,
  }
}

export function createFindingAssemblyAuditEvent({
  actorId,
  auditEventId,
  findingAssembly,
  occurredAt,
  scanId,
}: {
  actorId: string
  auditEventId: string
  findingAssembly: FindingAssemblySummary
  occurredAt: string
  scanId: string
}): AuditEvent {
  return createAuditEvent({
    action: 'record_finding_assembly',
    actorId,
    auditEventId,
    eventType: 'finding_assembly_completed',
    objectId: `${scanId}:finding_assembly`,
    objectType: 'finding_assembly',
    occurredAt,
    outcome: 'completed',
    scanId,
    findingId: null,
    previousState: 'pending',
    resultingState: 'completed',
    stage: 'assembling_findings',
    summary: `Finding assembly produced ${findingAssembly.assembledFindings} findings and ${findingAssembly.evidenceCards} evidence cards with ${findingAssembly.missingEvidenceCards} missing cards.`,
    policyPackVersion: findingAssembly.policyPackVersion,
    evidenceReferences: [
      { type: 'source_snapshot', id: findingAssembly.sourceSnapshotId },
      { type: 'rule_fingerprint', id: findingAssembly.assemblyRulesFingerprint },
    ],
  })
}

function buildFinding({
  category,
  categoryIndex,
  findingIndex,
  governanceConfig,
  occurredAt,
  owner,
  riskLevel,
  scan,
  source,
  template,
}: {
  category: ContextCategorySummary
  categoryIndex: number
  findingIndex: number
  governanceConfig: GovernanceConfig
  occurredAt: string
  owner: Owner
  riskLevel: string
  scan: Scan
  source: Source
  template: FindingTemplate
}): Finding {
  const findingNumber = findingIndex + 1
  const suffix = String(findingNumber).padStart(3, '0')
  const fileYear = category.retentionRuleApplied ? 2021 : 2024
  const fileName = `${template.fileStem}_${fileYear}_${String(categoryIndex + 1).padStart(2, '0')}.${template.extension}`
  const guidance = findRiskGuidance(template.category, governanceConfig)
  const retentionStatus = category.retentionRuleApplied ? 'overdue' : 'review_required'
  const riskScore = scoreRisk(riskLevel, findingIndex)

  return {
    findingId: `finding_${suffix}`,
    scanId: scan.scanId,
    fileName,
    sourcePath: `${template.pathSegment}/${fileName}`,
    riskLevel,
    riskScore,
    contextCategory: template.category,
    personalDataTypes: template.signals.map((signal) => signal.type),
    retentionStatus,
    recommendedAction: riskLevel === 'high' ? 'escalate' : 'keep_with_reason',
    evidenceSignalCount: template.signals.length,
    policyPackVersion: governanceConfig.activePolicyPack.version,
    status: 'assigned',
    owner,
    file: {
      sourceName: source.name,
      sourceType: source.sourceType,
      lastModifiedAt: `${fileYear}-04-12T09:30:00Z`,
      sizeBytes: 640000 + (findingIndex * 27000),
    },
    signals: template.signals,
    riskExplanation: `${humanSentence(template.title)} contains redacted ${template.signals.map((signal) => signal.type.replaceAll('_', ' ')).join(', ')} evidence. ${guidance ?? 'Policy guidance is unavailable, so human review is required.'}`,
    policyContext: {
      policyPackId: governanceConfig.activePolicyPack.policyPackId,
      policyPackVersion: governanceConfig.activePolicyPack.version,
      policyConclusion: 'human_review_required',
    },
    availableActions: ['delete_candidate', 'keep_with_reason', 'correct_false_positive', 'reassign_owner', 'escalate'],
    deniedActions: [
      {
        action: 'execute_real_deletion',
        reason: 'Real deletion is disabled in the prototype.',
      },
    ],
    auditTimeline: createTimeline(scan.scanId, `finding_${suffix}`, owner, occurredAt, governanceConfig.activePolicyPack.version),
  }
}

function toSummary(finding: Finding): FindingSummary {
  const {
    auditTimeline,
    availableActions,
    deniedActions,
    file,
    policyContext,
    riskExplanation,
    signals,
    ...summary
  } = finding

  void auditTimeline
  void availableActions
  void deniedActions
  void file
  void policyContext
  void riskExplanation
  void signals

  return summary
}

function createTimeline(
  scanId: string,
  findingId: string,
  owner: Owner,
  occurredAt: string,
  policyPackVersion: string,
): AuditEvent[] {
  return [
    createAuditEvent({
      action: 'assemble_evidence_card',
      actorId: 'system',
      auditEventId: `${findingId}_assembled`,
      eventType: 'finding_assembled',
      objectId: findingId,
      objectType: 'finding',
      occurredAt,
      outcome: 'completed',
      scanId,
      findingId,
      previousState: 'detected',
      resultingState: 'assembled',
      stage: 'assembling_findings',
      summary: 'Evidence card assembled from redacted detector signals, context, owner routing, and policy context.',
      policyPackVersion,
      evidenceReferences: [
        { type: 'finding', id: findingId, label: 'redacted evidence card' },
        { type: 'policy_pack', id: policyPackVersion },
      ],
    }),
    createAuditEvent({
      action: 'assign_finding_owner',
      actorId: 'system',
      auditEventId: `${findingId}_assigned`,
      eventType: 'finding_assigned',
      objectId: findingId,
      objectType: 'finding',
      occurredAt,
      outcome: 'assigned',
      scanId,
      findingId,
      previousState: 'assembled',
      resultingState: 'assigned',
      stage: 'assigning_owner',
      summary: `Finding routed to ${owner.displayName}.`,
      policyPackVersion,
      evidenceReferences: [
        { type: 'finding', id: findingId, label: 'redacted evidence card' },
        { type: 'owner', id: owner.userId, label: owner.assignmentType },
      ],
    }),
  ]
}

function createRiskLevels(contextRisk: ContextRiskSummary): string[] {
  return [
    ...Array.from({ length: contextRisk.highRiskFindings }, () => 'high'),
    ...Array.from({ length: contextRisk.mediumRiskFindings }, () => 'medium'),
    ...Array.from({ length: contextRisk.lowRiskFindings }, () => 'low'),
  ]
}

function createOwners(ownerAssignment: OwnerAssignmentSummary): Owner[] {
  return [
    ...Array.from({ length: ownerAssignment.directOwnerAssignments }, (_, index) => directOwner(index)),
    ...Array.from({ length: ownerAssignment.masterOfDataAssignments }, () => fallbackOwner),
    ...Array.from({ length: ownerAssignment.escalationAssignments }, () => escalationOwner),
  ]
}

function directOwner(index: number): Owner {
  const directOwners = Object.values(findingTemplates).map((template) => template.owner)

  return directOwners[index % directOwners.length]
}

function countSignals(categories: ContextCategorySummary[]): number {
  return categories.reduce((total, category) => {
    const template = findingTemplates[category.contextCategory] ?? findingTemplates.incident_report

    return total + (category.flaggedFiles * template.signals.length)
  }, 0)
}

function findRiskGuidance(contextCategory: string, governanceConfig: GovernanceConfig): string | undefined {
  return governanceConfig.activePolicyPack.riskGuidance?.find((guidance) => (
    guidance.contextCategory === contextCategory
  ))?.reviewReason
}

function scoreRisk(riskLevel: string, index: number): number {
  if (riskLevel === 'high') {
    return 88 - (index % 5)
  }

  if (riskLevel === 'low') {
    return 38 + (index % 3)
  }

  return 68 - (index % 7)
}

function humanSentence(value: string): string {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`
}

function buildWarnings(
  state: AssemblyState,
  contentExtraction: ContentExtractionSummary,
  ownerAssignment: OwnerAssignmentSummary,
  missingEvidenceCards: number,
): string[] {
  if (state === 'pending') {
    return ['Finding assembly waits for completed owner assignment and redacted signals.']
  }

  const warnings: string[] = []

  if (contentExtraction.rawContentExposed) {
    warnings.push('Raw content boundary requires review before evidence cards can be trusted.')
  }

  if (ownerAssignment.unownedFindings > 0) {
    warnings.push(`${ownerAssignment.unownedFindings} findings are missing accountable routing.`)
  }

  if (missingEvidenceCards > 0) {
    warnings.push(`${missingEvidenceCards} findings are missing evidence cards.`)
  }

  return warnings
}
