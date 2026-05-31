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
  WorkspaceAdminSummary,
  WorkspaceDirectory,
  Workspace,
  WorkspaceGroup,
  WorkspaceMembership,
  WorkspaceInvitation,
} from '../types'
import type { StartScanOptions } from './scanWorkflow'

export type CreateSourceInput = {
  googleDriveAccessToken?: string
  sourceId: string
  name: string
  sourceType: string
  status?: string
  rootLabel?: string
  masterOfDataUserId?: string
  config?: Record<string, unknown>
}

export type GoogleDrivePickerConfig = {
  apiKey: string | null
  appId: string | null
  clientId: string | null
  configured: boolean
  missing: string[]
  scopes: {
    files: string
    folders: string
  }
}

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
  code?: string
  detail?: string
  title?: string
  traceId?: string
}

const apiBase = (import.meta.env.VITE_DATASENTINEL_API_BASE ?? '/api').replace(/\/$/, '')
const actorId = 'user_demo_admin'

export class ApiRequestError extends Error {
  code?: string
  problem: ProblemDetails
  status: number

  constructor(message: string, status: number, problem: ProblemDetails) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.problem = problem
    this.code = problem.code
  }
}

export function isApiRequestError(error: unknown): error is ApiRequestError {
  return error instanceof ApiRequestError
}

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
    workspaceDirectoryEnvelope,
    workspaceAdminEnvelope,
  ] = await Promise.all([
    requestEnvelope<Source[]>('/sources'),
    requestEnvelope<Scan>('/scans/current'),
    requestEnvelope<FindingSummary[]>('/findings'),
    requestEnvelope<AuditEvent[]>('/audit/events'),
    requestEnvelope<AdminMetrics>('/admin/metrics'),
    requestEnvelope<EvaluationSummary>('/evaluation/runs/latest'),
    requestEnvelope<GovernanceConfig>('/governance/config'),
    requestEnvelope<PermissionBoundary>('/users/me/permissions'),
    requestEnvelope<WorkspaceDirectory>('/workspaces'),
    requestEnvelope<WorkspaceAdminSummary>('/workspaces/current/admin'),
  ])
  const primaryFindingId = findingsEnvelope.data[0]?.findingId ?? fallback.findingDetail.findingId
  const [findingEnvelope, reviewSupportEnvelope] = primaryFindingId
    ? await Promise.all([
        requestEnvelope<Finding>(`/findings/${primaryFindingId}`),
        requestEnvelope<ReviewSupport>(`/findings/${primaryFindingId}/review-support`),
      ])
    : [
        { data: fallback.findingDetail, meta: findingsEnvelope.meta },
        { data: fallback.reviewSupport, meta: findingsEnvelope.meta },
      ]

  return {
    ...fallback,
    sources: sourcesEnvelope.data,
    scan: scanEnvelope.data,
    findings: findingsEnvelope.data,
    findingDetail: findingEnvelope.data,
    findingDetails: findingEnvelope.data.findingId
      ? {
          ...fallback.findingDetails,
          [findingEnvelope.data.findingId]: findingEnvelope.data,
        }
      : fallback.findingDetails,
    auditEvents: auditEventsEnvelope.data,
    metrics: normalizeAdminMetrics(metricsEnvelope.data),
    evaluation: evaluationEnvelope.data,
    governanceConfig: governanceEnvelope.data,
    permissionBoundary: permissionEnvelope.data,
    reviewSupport: reviewSupportEnvelope.data,
    workspaceDirectory: workspaceDirectoryEnvelope.data,
    workspaceAdmin: workspaceAdminEnvelope.data,
    meta: combineMeta([
      sourcesEnvelope.meta,
      scanEnvelope.meta,
      findingsEnvelope.meta,
      auditEventsEnvelope.meta,
      metricsEnvelope.meta,
      evaluationEnvelope.meta,
      governanceEnvelope.meta,
      permissionEnvelope.meta,
      workspaceDirectoryEnvelope.meta,
      workspaceAdminEnvelope.meta,
      findingEnvelope.meta,
      reviewSupportEnvelope.meta,
    ]),
  }
}

function normalizeAdminMetrics(metrics: AdminMetrics): AdminMetrics {
  if (!metrics.aggregation || isStructuredAggregation(metrics.aggregation)) {
    return metrics
  }

  const metricsWithoutAggregation = { ...metrics }
  delete metricsWithoutAggregation.aggregation
  return metricsWithoutAggregation
}

function isStructuredAggregation(aggregation: AdminMetrics['aggregation']) {
  return Boolean(
    aggregation
    && Array.isArray(aggregation.inputStages)
    && aggregation.scanCoverage
    && aggregation.risk
    && aggregation.ownerBacklog
    && aggregation.outcomes
    && aggregation.audit
    && Array.isArray(aggregation.warnings),
  )
}

export async function startServerScan(options: StartScanOptions): Promise<ApiEnvelope<Scan>> {
  const path = options.scanType === 'delta' ? '/scans/delta' : '/scans/full'

  return requestEnvelope<Scan>(path, {
    body: JSON.stringify({
      authorization: options.googleDriveAccessToken ? { googleDriveAccessToken: options.googleDriveAccessToken } : undefined,
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

export async function createServerSource(input: CreateSourceInput): Promise<ApiEnvelope<Source>> {
  const payload: Partial<CreateSourceInput> = { ...input }
  delete payload.googleDriveAccessToken
  return requestEnvelope<Source>('/sources', {
    body: JSON.stringify(payload),
    headers: jsonHeaders({ idempotencyKey: `source_${input.sourceId}` }),
    method: 'POST',
  })
}

export async function deleteServerSource(sourceId: string): Promise<ApiEnvelope<Source>> {
  return requestEnvelope<Source>(`/sources/${encodeURIComponent(sourceId)}`, {
    headers: jsonHeaders({ idempotencyKey: `delete_source_${sourceId}_${Date.now()}` }),
    method: 'DELETE',
  })
}

export async function loadGoogleDrivePickerConfig(): Promise<ApiEnvelope<GoogleDrivePickerConfig>> {
  return requestEnvelope<GoogleDrivePickerConfig>('/integrations/google-drive/picker-config')
}

export async function reviewServerFinding(input: ReviewInput): Promise<ApiEnvelope<ReviewRecord>> {
  return requestEnvelope<ReviewRecord>(`/findings/${input.findingId}/review`, {
    body: JSON.stringify(input),
    headers: jsonHeaders({ idempotencyKey: input.idempotencyKey ?? `review_${input.findingId}_${Date.now()}` }),
    method: 'POST',
  })
}

export async function createServerWorkspace(input: {
  description?: string
  name: string
}): Promise<ApiEnvelope<WorkspaceDirectory>> {
  return requestEnvelope<WorkspaceDirectory>('/workspaces', {
    body: JSON.stringify(input),
    headers: jsonHeaders({ idempotencyKey: `workspace_create_${input.name}` }),
    method: 'POST',
  })
}

export async function switchServerWorkspace(workspaceId: string): Promise<ApiEnvelope<WorkspaceDirectory>> {
  return requestEnvelope<WorkspaceDirectory>('/workspaces/current', {
    body: JSON.stringify({ workspaceId }),
    headers: jsonHeaders({ idempotencyKey: `workspace_switch_${workspaceId}_${Date.now()}` }),
    method: 'POST',
  })
}

export async function createServerWorkspaceInvitation(input: {
  groupIds: string[]
  workspaceId: string
}): Promise<ApiEnvelope<WorkspaceInvitation>> {
  return requestEnvelope<WorkspaceInvitation>(`/workspaces/${encodeURIComponent(input.workspaceId)}/invitations`, {
    body: JSON.stringify({
      groupIds: input.groupIds,
    }),
    headers: jsonHeaders({ idempotencyKey: `workspace_invite_link_${input.workspaceId}_${Date.now()}` }),
    method: 'POST',
  })
}

export async function createServerWorkspaceGroup(input: {
  description?: string
  name: string
  permissions: string[]
  workspaceId: string
}): Promise<ApiEnvelope<WorkspaceGroup>> {
  return requestEnvelope<WorkspaceGroup>(`/workspaces/${encodeURIComponent(input.workspaceId)}/groups`, {
    body: JSON.stringify({
      description: input.description,
      name: input.name,
      permissions: input.permissions,
    }),
    headers: jsonHeaders({ idempotencyKey: `workspace_group_create_${input.workspaceId}_${input.name}` }),
    method: 'POST',
  })
}

export async function updateServerWorkspaceGroup(input: {
  description?: string
  groupId: string
  name: string
  permissions: string[]
  workspaceId: string
}): Promise<ApiEnvelope<WorkspaceGroup>> {
  return requestEnvelope<WorkspaceGroup>(`/workspaces/${encodeURIComponent(input.workspaceId)}/groups/${encodeURIComponent(input.groupId)}`, {
    body: JSON.stringify({
      description: input.description,
      name: input.name,
      permissions: input.permissions,
    }),
    headers: jsonHeaders({ idempotencyKey: `workspace_group_update_${input.workspaceId}_${input.groupId}_${Date.now()}` }),
    method: 'PATCH',
  })
}

export async function deleteServerWorkspaceGroup(input: {
  groupId: string
  workspaceId: string
}): Promise<ApiEnvelope<WorkspaceGroup>> {
  return requestEnvelope<WorkspaceGroup>(`/workspaces/${encodeURIComponent(input.workspaceId)}/groups/${encodeURIComponent(input.groupId)}`, {
    headers: jsonHeaders({ idempotencyKey: `workspace_group_delete_${input.workspaceId}_${input.groupId}_${Date.now()}` }),
    method: 'DELETE',
  })
}

export async function updateServerWorkspaceMember(input: {
  groupIds: string[]
  membershipId: string
  workspaceId: string
}): Promise<ApiEnvelope<WorkspaceMembership>> {
  return requestEnvelope<WorkspaceMembership>(`/workspaces/${encodeURIComponent(input.workspaceId)}/members/${encodeURIComponent(input.membershipId)}`, {
    body: JSON.stringify({
      groupIds: input.groupIds,
    }),
    headers: jsonHeaders({ idempotencyKey: `workspace_member_update_${input.workspaceId}_${input.membershipId}_${Date.now()}` }),
    method: 'PATCH',
  })
}

export async function deleteServerWorkspaceMember(input: {
  membershipId: string
  workspaceId: string
}): Promise<ApiEnvelope<WorkspaceMembership>> {
  return requestEnvelope<WorkspaceMembership>(`/workspaces/${encodeURIComponent(input.workspaceId)}/members/${encodeURIComponent(input.membershipId)}`, {
    headers: jsonHeaders({ idempotencyKey: `workspace_member_delete_${input.workspaceId}_${input.membershipId}_${Date.now()}` }),
    method: 'DELETE',
  })
}

export async function transferServerWorkspaceOwner(input: {
  membershipId: string
  workspaceId: string
}): Promise<ApiEnvelope<WorkspaceMembership>> {
  return requestEnvelope<WorkspaceMembership>(`/workspaces/${encodeURIComponent(input.workspaceId)}/owner-transfer`, {
    body: JSON.stringify({
      membershipId: input.membershipId,
    }),
    headers: jsonHeaders({ idempotencyKey: `workspace_owner_transfer_${input.workspaceId}_${input.membershipId}_${Date.now()}` }),
    method: 'POST',
  })
}

export async function deleteServerWorkspace(input: {
  workspaceId: string
  workspaceName: string
}): Promise<ApiEnvelope<Workspace>> {
  return requestEnvelope<Workspace>(`/workspaces/${encodeURIComponent(input.workspaceId)}`, {
    body: JSON.stringify({
      workspaceName: input.workspaceName,
    }),
    headers: jsonHeaders({ idempotencyKey: `workspace_delete_${input.workspaceId}_${Date.now()}` }),
    method: 'DELETE',
  })
}

export async function acceptServerWorkspaceInvitation(invitationId: string): Promise<ApiEnvelope<WorkspaceDirectory>> {
  return requestEnvelope<WorkspaceDirectory>(`/workspaces/invitations/${encodeURIComponent(invitationId)}/accept`, {
    body: '{}',
    headers: jsonHeaders({ idempotencyKey: `workspace_accept_${invitationId}` }),
    method: 'POST',
  })
}

async function requestEnvelope<T>(path: string, init: RequestInit = {}): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: 'include',
    headers: init.headers ?? jsonHeaders(),
  })

  if (!response.ok) {
    const problem = await readProblem(response)
    throw new ApiRequestError(problem.detail ?? problem.title ?? `API request failed with ${response.status}`, response.status, problem)
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
