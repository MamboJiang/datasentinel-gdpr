import type { MockData } from './mockApi'
import type {
  AdminMetrics,
  AuditEvent,
  EvaluationSummary,
  Finding,
  FindingSummary,
  GovernanceConfig,
  Meta,
  PermissionBoundary,
  ReviewInput,
  ReviewRecord,
  ReviewSupport,
  Scan,
  Source,
} from '../types'
import type { StartScanOptions } from './scanWorkflow'

type ApiEnvelope<T> = {
  data: T
  meta: Meta
  pagination?: {
    limit: number
    offset: number
    total: number
    nextCursor?: string | null
  }
}

type ConnectionResult = {
  connectionStatus: string
  diagnostics?: { message?: string }[]
  name?: string
  reachable?: boolean
}

type ProblemDetails = {
  detail?: string
  title?: string
  traceId?: string
}

const apiBase = (import.meta.env.VITE_DATASENTINEL_API_BASE ?? '/api').replace(/\/$/, '')
const actorId = 'user_demo_admin'

export async function loadServerData(fallback: MockData): Promise<MockData> {
  const [
    sourcesEnvelope,
    scanEnvelope,
    findingsEnvelope,
    auditEventsEnvelope,
    metricsEnvelope,
    evaluationEnvelope,
    governanceEnvelope,
    permissionEnvelope,
  ] = await Promise.all([
    requestEnvelope<Source[]>('/sources'),
    requestEnvelope<Scan>(`/scans/${fallback.scan.scanId}`),
    requestEnvelope<FindingSummary[]>('/findings'),
    requestEnvelope<AuditEvent[]>('/audit/events'),
    requestEnvelope<AdminMetrics>('/admin/metrics'),
    requestEnvelope<EvaluationSummary>('/evaluation/runs/latest'),
    requestEnvelope<GovernanceConfig>('/governance/config'),
    requestEnvelope<PermissionBoundary>('/users/me/permissions'),
  ])
  const primaryFindingId = findingsEnvelope.data[0]?.findingId ?? fallback.findingDetail.findingId
  const [findingEnvelope, reviewSupportEnvelope] = await Promise.all([
    requestEnvelope<Finding>(`/findings/${primaryFindingId}`),
    requestEnvelope<ReviewSupport>(`/findings/${primaryFindingId}/review-support`),
  ])

  return {
    ...fallback,
    sources: sourcesEnvelope.data,
    scan: scanEnvelope.data,
    findings: findingsEnvelope.data,
    findingDetail: findingEnvelope.data,
    findingDetails: {
      ...fallback.findingDetails,
      [findingEnvelope.data.findingId]: findingEnvelope.data,
    },
    auditEvents: auditEventsEnvelope.data,
    metrics: metricsEnvelope.data,
    evaluation: evaluationEnvelope.data,
    governanceConfig: governanceEnvelope.data,
    permissionBoundary: permissionEnvelope.data,
    reviewSupport: reviewSupportEnvelope.data,
    meta: combineMeta([
      sourcesEnvelope.meta,
      scanEnvelope.meta,
      findingsEnvelope.meta,
      auditEventsEnvelope.meta,
      metricsEnvelope.meta,
      evaluationEnvelope.meta,
      governanceEnvelope.meta,
      permissionEnvelope.meta,
      findingEnvelope.meta,
      reviewSupportEnvelope.meta,
    ]),
  }
}

export async function startServerScan(options: StartScanOptions): Promise<ApiEnvelope<Scan>> {
  const path = options.scanType === 'delta' ? '/scans/delta' : '/scans/full'

  return requestEnvelope<Scan>(path, {
    body: JSON.stringify({
      baselineScanId: options.baselineScanId,
      modifiedSince: options.modifiedSince,
      sourceId: options.sourceId,
    }),
    headers: jsonHeaders({ idempotencyKey: `scan_${options.scanType}_${Date.now()}` }),
    method: 'POST',
  })
}

export async function testServerSourceConnection(sourceId: string): Promise<ApiEnvelope<ConnectionResult>> {
  return requestEnvelope<ConnectionResult>(`/sources/${sourceId}/connect-test`, {
    body: '{}',
    headers: jsonHeaders(),
    method: 'POST',
  })
}

export async function reviewServerFinding(input: ReviewInput): Promise<ApiEnvelope<ReviewRecord>> {
  return requestEnvelope<ReviewRecord>(`/findings/${input.findingId}/review`, {
    body: JSON.stringify(input),
    headers: jsonHeaders({ idempotencyKey: input.idempotencyKey ?? `review_${input.findingId}_${Date.now()}` }),
    method: 'POST',
  })
}

async function requestEnvelope<T>(path: string, init: RequestInit = {}): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: init.headers ?? jsonHeaders(),
  })

  if (!response.ok) {
    const problem = await readProblem(response)
    throw new Error(problem.detail ?? problem.title ?? `API request failed with ${response.status}`)
  }

  return response.json() as Promise<ApiEnvelope<T>>
}

function jsonHeaders(options: { idempotencyKey?: string } = {}) {
  const headers = new Headers({
    Accept: 'application/json, application/problem+json',
    'Content-Type': 'application/json',
    'X-Actor-Id': actorId,
    'X-Contract-Version': '0.1.0',
  })

  if (options.idempotencyKey) {
    headers.set('Idempotency-Key', options.idempotencyKey)
  }

  return headers
}

async function readProblem(response: Response): Promise<ProblemDetails> {
  try {
    return await response.json() as ProblemDetails
  } catch {
    return { detail: response.statusText }
  }
}

function combineMeta(metas: Meta[]): Meta {
  const latest = metas[metas.length - 1]
  const warnings = metas.flatMap((item) => item.warnings ?? [])

  return {
    contractVersion: latest.contractVersion,
    generatedAt: latest.generatedAt,
    partial: metas.some((item) => item.partial),
    traceId: latest.traceId,
    warnings,
  }
}
