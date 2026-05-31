import { describe, expect, it } from 'vitest'
import { getInitialMockData, type MockData } from './mockApi'
import {
  buildReviewSupport,
  validateReviewInput,
} from './reviewSupport'
import {
  completeScanWorkflow,
  startScanWorkflow,
} from './scanWorkflow'

const startedAt = '2026-05-30T12:30:00.000Z'
const completedAt = '2026-05-30T12:30:38.200Z'

function completeStartedScan(data: MockData = getInitialMockData()) {
  const started = startScanWorkflow(data, {
    actorId: 'user_demo_admin',
    auditEventId: 'audit_started',
    occurredAt: startedAt,
    scanType: 'full',
    sourceId: 'source_001',
  })

  if (!started.accepted) {
    throw new Error('Expected full scan start to be accepted.')
  }

  return completeScanWorkflow(started.data, {
    auditEventId: 'audit_completed',
    occurredAt: completedAt,
    scanId: started.scanId,
  })
}

describe('review support and permission boundary workflow', () => {
  it('keeps review support connected to finding assembly, policy, permissions, metrics, and evaluation', () => {
    const completed = completeStartedScan()
    const summary = completed.scan.reviewSupport

    expect(completed.scan.pipelineStages?.map((stage) => stage.stage).slice(-3)).toEqual([
      'preparing_review_support',
      'recording_audit_events',
      'generating_evaluation_metrics',
    ])
    expect(summary).toMatchObject({
      status: 'completed',
      policyPackVersion: completed.governanceConfig.activePolicyPack.version,
      organizationModelVersion: completed.governanceConfig.organizationModel.version,
      reviewableFindings: completed.scan.findingAssembly?.evidenceCards,
      supportedFindings: completed.findings.length,
      availableDecisionCount: 5,
      reasonRequiredDecisionCount: 5,
      transferOptionCount: 1,
      escalationOptionCount: 1,
      rawContentExposed: false,
      legalConclusionProvided: false,
      warnings: [],
    })
    expect(completed.metrics).toMatchObject({
      reviewSupportedFindings: completed.findings.length,
      deniedReviewActions: 2,
      reviewChecklistItems: 5,
      reviewTransferOptions: 1,
      reviewEscalationOptions: 1,
    })
    expect(completed.evaluation.reviewSupportRulesHash).toBe(summary?.supportRulesFingerprint)
    expect(completed.evaluation.resourceIntensity).toMatchObject({
      modelCalls: 0,
      estimatedCostUsd: 0,
    })
  })

  it('builds finding-specific decisions, checklist, transfer options, and denied actions from the active governance model', () => {
    const completed = completeStartedScan()
    const finding = {
      ...completed.findingDetails.finding_001,
      owner: {
        assignmentReason: 'Assigned Source owner receives this review.',
        assignmentSource: 'source_assignment',
        assignmentType: 'direct_owner',
        displayName: 'Anna Privacy Reviewer',
        email: 'anna.reviewer@example.invalid',
        userId: 'user_anna',
      },
    }
    const support = buildReviewSupport({
      actorId: 'user_anna',
      finding,
      governanceConfig: completed.governanceConfig,
      occurredAt: completedAt,
    })
    const serialized = JSON.stringify(support)

    expect(support.findingId).toBe(finding.findingId)
    expect(support.availableDecisions.map((decision) => decision.decision)).toEqual([
      'delete_candidate',
      'keep_with_reason',
      'correct_false_positive',
      'reassign_owner',
      'escalate',
    ])
    expect(support.availableDecisions.every((decision) => decision.requiresReason)).toBe(true)
    expect(support.checklist.map((item) => item.itemId)).toEqual([
      'review_redacted_evidence',
      'confirm_business_purpose',
      'confirm_permission_boundary',
      'confirm_retention_context',
      'consider_escalation_path',
      'confirm_delete_candidate',
    ])
    expect(support.transferOptions).toEqual([
      {
        userId: 'user_markus',
        displayName: 'Markus Keller',
        reason: 'IT Operations owner available for controlled handoff.',
      },
    ])
    expect(support.escalationOptions).toEqual([
      {
        queueId: 'legal_escalation',
        label: 'Escalate to DPO or Legal',
      },
    ])
    expect(support.permissionBoundary?.deniedActions).toEqual([
      {
        action: 'activate_policy_pack',
        reason: 'Governance admin role is required.',
      },
      {
        action: 'execute_real_deletion',
        reason: 'Real deletion is disabled in the prototype.',
      },
    ])
    expect(serialized).not.toContain('@example.com')
    expect(serialized).not.toContain('DE89')
  })

  it('uses active Workspace members for finding transfer targets without governance fixture fallback', () => {
    const completed = completeStartedScan()
    const finding = {
      ...completed.findingDetails.finding_001,
      owner: {
        assignmentReason: 'Assigned Source owner receives this review.',
        assignmentSource: 'source_assignment',
        assignmentType: 'direct_owner',
        displayName: 'Anna Privacy Reviewer',
        email: 'anna.reviewer@example.invalid',
        userId: 'user_anna',
      },
    }
    const workspaceMembers = [
      {
        accountId: 'user_anna',
        displayName: 'Anna Privacy Reviewer',
        email: 'anna.reviewer@example.invalid',
        groupIds: ['privacy_reviewer'],
        invitedBy: null,
        joinedAt: startedAt,
        lastActiveAt: completedAt,
        membershipId: 'mem_anna',
        status: 'active',
        workspaceId: 'ws_datasentinel_gdpr',
      },
      {
        accountId: 'user_marta',
        displayName: 'Marta Data Steward',
        email: 'marta.steward@example.invalid',
        groupIds: ['data_steward'],
        invitedBy: 'user_demo_admin',
        joinedAt: startedAt,
        lastActiveAt: completedAt,
        membershipId: 'mem_marta',
        status: 'active',
        workspaceId: 'ws_datasentinel_gdpr',
      },
    ]

    const support = buildReviewSupport({
      actorId: 'user_anna',
      finding,
      governanceConfig: completed.governanceConfig,
      occurredAt: completedAt,
      workspaceMembers,
    })
    const emptyWorkspaceSupport = buildReviewSupport({
      actorId: 'user_anna',
      finding,
      governanceConfig: completed.governanceConfig,
      occurredAt: completedAt,
      workspaceMembers: [],
    })

    expect(support.transferOptions?.map((option) => option.userId)).toEqual(['user_marta'])
    expect(support.transferOptions?.map((option) => option.userId)).not.toContain('user_markus')
    expect(emptyWorkspaceSupport.transferOptions).toEqual([])
  })

  it('rejects decisions outside the permission boundary or without required human context', () => {
    const completed = completeStartedScan()
    const finding = completed.findingDetails.finding_001
    const guestSupport = buildReviewSupport({
      actorId: 'user_guest',
      finding,
      governanceConfig: completed.governanceConfig,
      occurredAt: completedAt,
    })
    const reviewerSupport = buildReviewSupport({
      actorId: 'user_anna',
      finding,
      governanceConfig: completed.governanceConfig,
      occurredAt: completedAt,
    })

    expect(guestSupport.availableDecisions).toEqual([])
    expect(validateReviewInput({
      findingId: finding.findingId,
      decision: 'keep_with_reason',
      reason: 'Reviewed business purpose.',
      actorId: 'user_guest',
    }, guestSupport)).toMatchObject({
      accepted: false,
      reason: 'Keep with business reason is outside the current permission boundary.',
    })
    expect(validateReviewInput({
      findingId: finding.findingId,
      decision: 'keep_with_reason',
      reason: '',
      actorId: 'user_anna',
    }, reviewerSupport)).toMatchObject({
      accepted: false,
      reason: 'A human review decision requires a recorded reason.',
    })
    expect(validateReviewInput({
      findingId: finding.findingId,
      decision: 'reassign_owner',
      reason: 'Ownership is better handled by IT Operations.',
      actorId: 'user_anna',
      checklistItemIds: reviewerSupport.checklist.map((item) => item.itemId),
    }, reviewerSupport)).toMatchObject({
      accepted: false,
      reason: 'Transfer decisions require a target owner.',
    })
  })

  it('does not prepare review support for a not-ready source', () => {
    const data = getInitialMockData()
    const result = startScanWorkflow(data, {
      actorId: 'user_demo_admin',
      auditEventId: 'audit_blocked',
      occurredAt: startedAt,
      scanType: 'full',
      sourceId: 'source_002',
    })

    expect(result.accepted).toBe(false)
    expect(result.data.scan.reviewSupport).toEqual(data.scan.reviewSupport)
    expect(result.data.reviewSupport).toEqual(data.reviewSupport)
    expect(result.data.permissionBoundary).toEqual(data.permissionBoundary)
  })
})
