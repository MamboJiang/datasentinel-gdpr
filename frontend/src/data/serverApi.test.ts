import { afterEach, describe, expect, it, vi } from 'vitest'
import { getEmptyData } from './emptyData'
import { getServerFinding, isApiRequestError, loadServerData, startServerScan, switchServerWorkspace } from './serverApi'

function envelope(data: unknown) {
  return {
    data,
    meta: {
      contractVersion: '0.1.0',
      generatedAt: '2026-05-31T00:00:00Z',
      traceId: 'trace_test',
      partial: false,
      warnings: [],
    },
  }
}

describe('server API loading', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads an authenticated empty prelaunch project without requesting a blank finding detail', async () => {
    const fallback = getEmptyData()
    const partialMetrics = {
      ...fallback.metrics,
      aggregation: {
        estimatedCostUsd: 0,
        modelCalls: 0,
      },
    }
    const payloads = new Map<string, unknown>([
      ['/sources', []],
      ['/scans/current', fallback.scan],
      ['/findings', []],
      ['/audit/events', []],
      ['/admin/metrics', partialMetrics],
      ['/evaluation/runs/latest', fallback.evaluation],
      ['/governance/config', fallback.governanceConfig],
      ['/users/me/permissions', fallback.permissionBoundary],
      ['/workspaces', fallback.workspaceDirectory],
      ['/workspaces/current/admin', fallback.workspaceAdmin],
    ])
    const requestedPaths: string[] = []

    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input).replace('/api', '')
      requestedPaths.push(path)
      const payload = payloads.get(path)

      if (payload === undefined) {
        return new Response(JSON.stringify({
          detail: `Unexpected path ${path}`,
          title: 'Unexpected request',
        }), { status: 404 })
      }

      return new Response(JSON.stringify(envelope(payload)), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      })
    }))

    const data = await loadServerData(fallback)

    expect(data.findings).toEqual([])
    expect(data.findingDetail.findingId).toBe('')
    expect(data.reviewSupport.findingId).toBe('')
    expect(data.metrics.aggregation).toBeUndefined()
    expect(requestedPaths).not.toContain('/findings/')
    expect(requestedPaths).not.toContain('/findings//review-support')
  })

  it('posts the selected Workspace when switching current Workspace context', async () => {
    const fallback = getEmptyData()
    const requests: { body?: string; path: string }[] = []

    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      requests.push({
        body: typeof init?.body === 'string' ? init.body : undefined,
        path: String(input).replace('/api', ''),
      })
      return new Response(JSON.stringify(envelope({
        ...fallback.workspaceDirectory,
        currentWorkspaceId: 'ws_target',
      })), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      })
    }))

    const switched = await switchServerWorkspace('ws_target')

    expect(requests).toEqual([{ body: JSON.stringify({ workspaceId: 'ws_target' }), path: '/workspaces/current' }])
    expect(switched.data.currentWorkspaceId).toBe('ws_target')
  })

  it('loads a requested finding detail by id instead of relying on the first list row', async () => {
    const requests: string[] = []

    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      requests.push(String(input).replace('/api', ''))
      return new Response(JSON.stringify(envelope({
        findingId: 'finding_target',
        fileName: 'target.csv',
        riskLevel: 'high',
        riskScore: 91,
        signals: [{ confidence: 0.98, detector: 'regex', snippet: '[REDACTED_EMAIL]', type: 'email' }],
        status: 'assigned',
      })), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      })
    }))

    const detail = await getServerFinding('finding_target')

    expect(requests).toEqual(['/findings/finding_target'])
    expect(detail.data.signals).toHaveLength(1)
  })

  it('preserves API rejection status so callers do not treat command rejection as server outage', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      code: 'command-rejected',
      detail: 'Google Drive scans require a short-lived access token.',
      title: 'Command rejected',
    }), {
      headers: { 'Content-Type': 'application/problem+json' },
      status: 409,
    })))

    await expect(startServerScan({ scanType: 'full', sourceId: 'source_drive' })).rejects.toMatchObject({
      message: 'Google Drive scans require a short-lived access token.',
      status: 409,
    })

    try {
      await startServerScan({ scanType: 'full', sourceId: 'source_drive' })
    } catch (error) {
      expect(isApiRequestError(error)).toBe(true)
    }
  })
})
