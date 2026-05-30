import type { AuditEvent, OwnerAssignmentSummary } from '../types'
import { createAuditEvent } from './auditEventRecording'
import { formatScanType } from './scanLabels'

export function createScanAuditEvent({
  actorId,
  auditEventId,
  eventType,
  occurredAt,
  policyPackVersion,
  previousState,
  scanId,
  scanType,
  sourceId,
  sourceName,
}: {
  actorId: string
  auditEventId: string
  eventType: string
  occurredAt: string
  policyPackVersion: string
  previousState: string
  scanId: string
  scanType: string
  sourceId: string
  sourceName: string
}): AuditEvent {
  const completed = eventType.endsWith('completed')

  return createAuditEvent({
    action: completed ? 'complete_scan' : 'start_scan',
    actorId,
    auditEventId,
    eventType,
    objectId: scanId,
    objectType: 'scan',
    occurredAt,
    outcome: completed ? 'completed' : 'accepted',
    scanId,
    findingId: null,
    sourceId,
    previousState,
    resultingState: completed ? 'completed' : 'running',
    stage: completed ? 'completed' : 'extracting_content',
    summary: `${formatScanType(scanType)} scan ${eventType.endsWith('started') ? 'started' : 'completed'} for ${sourceName}.`,
    policyPackVersion,
    evidenceReferences: [
      { type: 'source', id: sourceId, label: sourceName },
      { type: 'policy_pack', id: policyPackVersion },
    ],
  })
}

export function createOwnerAssignmentAuditEvent({
  actorId,
  auditEventId,
  occurredAt,
  ownerAssignment,
  scanId,
}: {
  actorId: string
  auditEventId: string
  occurredAt: string
  ownerAssignment: OwnerAssignmentSummary
  scanId: string
}): AuditEvent {
  return createAuditEvent({
    action: 'record_owner_assignment',
    actorId,
    auditEventId,
    eventType: 'owner_assignment_completed',
    objectId: `${scanId}:owner_assignment`,
    objectType: 'owner_assignment',
    occurredAt,
    outcome: 'completed',
    scanId,
    findingId: null,
    previousState: 'pending',
    resultingState: 'completed',
    stage: 'assigning_owner',
    summary: `Owner routing assigned ${ownerAssignment.assignedFindings} findings: ${ownerAssignment.directOwnerAssignments} direct owner, ${ownerAssignment.masterOfDataAssignments} Master of Data fallback, ${ownerAssignment.escalationAssignments} escalation route, ${ownerAssignment.unownedFindings} unowned.`,
    policyPackVersion: ownerAssignment.policyPackVersion,
    evidenceReferences: [
      { type: 'policy_pack', id: ownerAssignment.policyPackVersion },
      { type: 'organization_model', id: ownerAssignment.organizationModelVersion },
      { type: 'rule_fingerprint', id: ownerAssignment.assignmentRulesFingerprint },
    ],
  })
}
