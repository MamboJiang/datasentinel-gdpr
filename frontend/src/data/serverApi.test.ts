import { afterEach, describe, expect, it, vi } from 'vitest'
import { getEmptyData } from './emptyData'
import { loadServerData } from './serverApi'

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
})
