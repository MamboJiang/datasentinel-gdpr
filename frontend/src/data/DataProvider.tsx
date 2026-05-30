import { useEffect, useRef, useState, type ReactNode } from 'react'
import { DataContext } from './DataContext'
import { recordHumanReviewDecision } from './humanReviewDecision'
import { getInitialMockData } from './mockApi'
import { buildReviewSupport } from './reviewSupport'
import { completeScanWorkflow, getSourceConnectionMessage, startScanWorkflow, type StartScanOptions } from './scanWorkflow'
import { loadServerData, reviewServerFinding, startServerScan, testServerSourceConnection } from './serverApi'
import type {
  Finding,
  ReviewInput,
} from '../types'

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState(getInitialMockData)
  const [toast, setToast] = useState<string | null>(null)
  const scanTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const serverAvailable = useRef(false)

  useEffect(() => {
    let active = true
    const fallback = getInitialMockData()

    loadServerData(fallback)
      .then((serverData) => {
        if (!active) {
          return
        }

        serverAvailable.current = true
        setData(serverData)
      })
      .catch(() => {
        serverAvailable.current = false
      })

    return () => {
      active = false

      if (scanTimer.current) {
        clearTimeout(scanTimer.current)
      }
    }
  }, [])

  async function startScan(options: StartScanOptions) {
    if (serverAvailable.current) {
      try {
        const result = await startServerScan(options)

        if (scanTimer.current) {
          clearTimeout(scanTimer.current)
        }

        setData((current) => ({
          ...current,
          meta: result.meta,
          scan: result.data,
        }))
        setToast(`${options.scanType === 'full' ? 'Full' : 'Delta'} scan started on the project server.`)
        scanTimer.current = setTimeout(() => {
          refreshServerData(`${options.scanType === 'full' ? 'Full' : 'Delta'} scan completed.`)
          scanTimer.current = null
        }, options.scanType === 'full' ? 2400 : 2000)
        return
      } catch (error) {
        serverAvailable.current = false
        setToast(error instanceof Error ? error.message : 'Project server unavailable; using local mock workflow.')
      }
    }

    startLocalScan(options)
  }

  function startLocalScan(options: StartScanOptions) {
    const result = startScanWorkflow(data, {
      ...options,
      actorId: 'user_demo_admin',
      auditEventId: `audit_${Date.now()}`,
      occurredAt: new Date().toISOString(),
    })

    if (!result.accepted) {
      setToast(result.toast)
      return
    }

    if (scanTimer.current) {
      clearTimeout(scanTimer.current)
    }

    setData(result.data)
    setToast(result.toast)

    scanTimer.current = setTimeout(() => {
      setData((current) => completeScanWorkflow(current, {
        auditEventId: `audit_${Date.now()}`,
        occurredAt: new Date().toISOString(),
        scanId: result.scanId,
      }))
      setToast(`${options.scanType === 'full' ? 'Full' : 'Delta'} scan completed.`)
      scanTimer.current = null
    }, result.completionDelayMs)
  }

  async function testSourceConnection(sourceId: string) {
    if (serverAvailable.current) {
      try {
        const result = await testServerSourceConnection(sourceId)
        const diagnostics = result.data.diagnostics?.map((item) => item.message).filter(Boolean).join(' ')
        setToast(`${result.data.name ?? sourceId} connection: ${result.data.connectionStatus}.${diagnostics ? ` ${diagnostics}` : ''}`)
        return
      } catch (error) {
        serverAvailable.current = false
        setToast(error instanceof Error ? error.message : 'Project server unavailable; using local source check.')
      }
    }

    const source = data.sources.find((candidate) => candidate.sourceId === sourceId)
    setToast(getSourceConnectionMessage(source, data.governanceConfig))
  }

  async function reviewFinding(input: ReviewInput) {
    if (serverAvailable.current) {
      try {
        await reviewServerFinding(input)
        await refreshServerData('Review decision recorded. Deletion remains simulated.')
        return
      } catch (error) {
        serverAvailable.current = false
        setToast(error instanceof Error ? error.message : 'Project server unavailable; using local review workflow.')
      }
    }

    const occurredAt = new Date().toISOString()
    const finding = getFinding(input.findingId)
    const reviewSupport = finding
      ? buildReviewSupport({
          actorId: input.actorId,
          finding,
          governanceConfig: data.governanceConfig,
          occurredAt,
        })
      : data.reviewSupport
    const result = recordHumanReviewDecision(data, {
      ...input,
      auditEventId: `audit_${Date.now()}`,
      occurredAt,
      reviewId: `review_${Date.now()}`,
      reviewSupportRulesFingerprint: data.scan.reviewSupport?.supportRulesFingerprint,
    }, reviewSupport)

    if (!result.accepted) {
      setToast(result.reason)
      return
    }

    setData(result.data)
    setToast(result.toast)
  }

  function getFinding(findingId: string): Finding | undefined {
    if (data.findingDetails[findingId]) {
      return data.findingDetails[findingId]
    }

    if (data.findingDetail.findingId === findingId) {
      return data.findingDetail
    }

    return data.findings.find((finding) => finding.findingId === findingId)
  }

  function getReviewSupport(findingId: string) {
    const finding = getFinding(findingId)

    if (!finding) {
      return data.reviewSupport
    }

    return buildReviewSupport({
      actorId: data.permissionBoundary.actorId,
      finding,
      governanceConfig: data.governanceConfig,
      occurredAt: data.meta.generatedAt,
    })
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
        getReviewSupport,
        startScan,
        testSourceConnection,
        reviewFinding,
        clearToast: () => setToast(null),
      }}
    >
      {children}
    </DataContext.Provider>
  )

  async function refreshServerData(successToast: string) {
    const nextData = await loadServerData(getInitialMockData())
    serverAvailable.current = true
    setData(nextData)
    setToast(successToast)
  }
}
