import { useEffect, useRef, useState, type ReactNode } from 'react'
import { DataContext } from './DataContext'
import { getInitialMockData } from './mockApi'
import type {
  AuditEvent,
  Finding,
  FindingSummary,
  ReviewDecision,
  ReviewInput,
  Scan,
} from '../types'

const decisionStatus: Record<ReviewDecision, string> = {
  delete_candidate: 'delete_candidate',
  keep_with_reason: 'retained',
  correct_false_positive: 'false_positive',
  reassign_owner: 'assigned',
  escalate: 'escalated',
}

const decisionLabel: Record<ReviewDecision, string> = {
  delete_candidate: 'marked as a deletion candidate',
  keep_with_reason: 'retained with a documented reason',
  correct_false_positive: 'corrected as a false positive',
  reassign_owner: 'reassigned for review',
  escalate: 'escalated for additional review',
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState(getInitialMockData)
  const [toast, setToast] = useState<string | null>(null)
  const scanTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (scanTimer.current) {
        clearTimeout(scanTimer.current)
      }
    }
  }, [])

  function startScan(scanType: 'full' | 'delta') {
    if (scanTimer.current) {
      clearTimeout(scanTimer.current)
    }

    const scanId = scanType === 'full' ? 'scan_demo_full' : 'scan_demo_delta'
    const startedAt = new Date().toISOString()
    const sourceName = data.sources[0]?.name ?? 'configured source'
    const runningScan: Scan = {
      scanId,
      sourceId: data.sources[0]?.sourceId ?? 'source_001',
      scanType,
      status: 'running',
      progress: scanType === 'full' ? 0.34 : 0.67,
      totalFiles: scanType === 'full' ? 42 : 6,
      scannedFiles: scanType === 'full' ? 14 : 4,
      flaggedFiles: scanType === 'full' ? 5 : 2,
      totalBytes: scanType === 'full' ? 38210000 : 6240000,
      durationMs: null,
      throughputFilesPerSecond: null,
      reproducibilityFingerprint: null,
    }

    setData((current) => ({
      ...current,
      scan: runningScan,
      metrics: {
        ...current.metrics,
        scanProgress: runningScan.progress,
      },
      auditEvents: [
        {
          auditEventId: `audit_${Date.now()}`,
          scanId,
          findingId: null,
          eventType: `${scanType}_scan_started`,
          actorId: 'user_demo_admin',
          occurredAt: startedAt,
          summary: `${scanType === 'full' ? 'Full' : 'Delta'} scan started for ${sourceName}.`,
        },
        ...current.auditEvents,
      ],
    }))
    setToast(`${scanType === 'full' ? 'Full' : 'Delta'} scan started in simulated mode.`)

    scanTimer.current = setTimeout(() => {
      const completedAt = new Date().toISOString()
      setData((current) => {
        const completedScan: Scan = {
          ...current.scan,
          status: 'completed',
          progress: 1,
          scannedFiles: current.scan.totalFiles,
          durationMs: scanType === 'full' ? 38200 : 5200,
          throughputFilesPerSecond: scanType === 'full' ? 1.1 : 1.15,
          reproducibilityFingerprint: 'sha256:demo_findings',
        }

        return {
          ...current,
          scan: completedScan,
          metrics: {
            ...current.metrics,
            scanProgress: 1,
            lastScanTimeSeconds: scanType === 'full' ? 38.2 : 5.2,
          },
          auditEvents: [
            {
              auditEventId: `audit_${Date.now()}`,
              scanId,
              findingId: null,
              eventType: `${scanType}_scan_completed`,
              actorId: 'system',
              occurredAt: completedAt,
              summary: `${scanType === 'full' ? 'Full' : 'Delta'} scan completed for ${sourceName}.`,
            },
            ...current.auditEvents,
          ],
        }
      })
      setToast(`${scanType === 'full' ? 'Full' : 'Delta'} scan completed.`)
      scanTimer.current = null
    }, 2200)
  }

  function reviewFinding(input: ReviewInput) {
    const resultingStatus = decisionStatus[input.decision]
    const occurredAt = new Date().toISOString()
    const auditEvent: AuditEvent = {
      auditEventId: `audit_${Date.now()}`,
      scanId: data.findings.find((finding) => finding.findingId === input.findingId)?.scanId ?? null,
      findingId: input.findingId,
      eventType: 'review_recorded',
      actorId: input.actorId,
      occurredAt,
      summary: `Finding ${decisionLabel[input.decision]}.`,
      reason: input.reason,
      resultingStatus,
    }

    function updateFinding<T extends FindingSummary>(finding: T): T {
      if (finding.findingId !== input.findingId) {
        return finding
      }

      return {
        ...finding,
        status: resultingStatus,
      }
    }

    setData((current) => ({
      ...current,
      findings: current.findings.map(updateFinding),
      findingDetail:
        current.findingDetail.findingId === input.findingId
          ? {
              ...updateFinding(current.findingDetail),
              auditTimeline: [auditEvent, ...(current.findingDetail.auditTimeline ?? [])],
            }
          : current.findingDetail,
      auditEvents: [auditEvent, ...current.auditEvents],
      metrics: {
        ...current.metrics,
        openReviewBacklog: Math.max(0, current.metrics.openReviewBacklog - 1),
      },
    }))
    setToast('Review decision recorded. Deletion remains simulated.')
  }

  function getFinding(findingId: string): Finding | undefined {
    if (data.findingDetail.findingId === findingId) {
      return data.findingDetail
    }

    return data.findings.find((finding) => finding.findingId === findingId)
  }

  return (
    <DataContext.Provider
      value={{
        sources: data.sources,
        scan: data.scan,
        findings: data.findings,
        auditEvents: data.auditEvents,
        metrics: data.metrics,
        evaluation: data.evaluation,
        governanceConfig: data.governanceConfig,
        permissionBoundary: data.permissionBoundary,
        reviewSupport: data.reviewSupport,
        meta: data.meta,
        toast,
        getFinding,
        startScan,
        reviewFinding,
        clearToast: () => setToast(null),
      }}
    >
      {children}
    </DataContext.Provider>
  )
}
