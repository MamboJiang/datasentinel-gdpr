import { ApiRequestError } from './serverApi'

export type PublicAnalysisCapacity = {
  maxActive: number
  activeAnalyses: number
  availableSlots: number
  waitingUsers: number
  queueMode: string
  userHasActiveAnalysis: boolean
  userQueuePosition: number | null
  fileSizeLimitBytes: number
}

export type PublicAnalysisDetectedType = {
  type: string
  count: number
  highestConfidence: number
}

export type PublicAnalysisEvidence = {
  type: string
  detector: string
  confidence: number
  snippet: string
  locationLabel: string
}

export type PublicAnalysisStage = {
  name: string
  status?: string
  description?: string
}

export type PublicAnalysisResult = {
  analysisId: string
  status: string
  file: {
    name: string
    sizeBytes: number
    fileFormat: string
    extractionMethod: string
    recognitionDifficulty: string
  }
  summary: {
    detectedSignalCount: number
    detectedTypes: PublicAnalysisDetectedType[]
    riskLevel: string
    reviewRecommendation: string
    nextSteps?: string[]
    workflowReadiness?: string[]
    boundaryNotes?: string[]
    rawContentExposed: boolean
    legalConclusionProvided: boolean
    deletionAvailable: boolean
  }
  analysisStages?: PublicAnalysisStage[]
  governanceBoundaries?: string[]
  evidence: PublicAnalysisEvidence[]
  warnings: string[]
  capacity: PublicAnalysisCapacity
}

type ApiEnvelope<T> = {
  data: T
  meta: {
    contractVersion: string
    generatedAt: string
    traceId: string
    partial: boolean
    warnings: string[]
  }
}

export type PublicAnalysisProblem = {
  capacity?: PublicAnalysisCapacity
  code?: string
  detail?: string
  title?: string
  traceId?: string
}

const apiBase = (import.meta.env.VITE_LAWDIT_API_BASE ?? '/api').replace(/\/$/, '')

export async function loadPublicAnalysisCapacity(sessionId: string): Promise<ApiEnvelope<PublicAnalysisCapacity>> {
  return requestPublicEnvelope<PublicAnalysisCapacity>('/public-analysis/capacity', {
    headers: publicHeaders(sessionId),
    method: 'GET',
  })
}

export async function analyzePublicFile(file: File, sessionId: string): Promise<ApiEnvelope<PublicAnalysisResult>> {
  const body = new FormData()
  body.append('file', file, file.name)

  return requestPublicEnvelope<PublicAnalysisResult>('/public-analysis/analyze', {
    body,
    headers: publicHeaders(sessionId),
    method: 'POST',
  })
}

async function requestPublicEnvelope<T>(path: string, init: RequestInit): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: 'include',
  })

  if (!response.ok) {
    const problem = await readProblem(response)
    throw new ApiRequestError(problem.detail ?? problem.title ?? `API request failed with ${response.status}`, response.status, problem)
  }

  return response.json() as Promise<ApiEnvelope<T>>
}

function publicHeaders(sessionId: string) {
  return new Headers({
    Accept: 'application/json, application/problem+json',
    'X-Contract-Version': '0.1.0',
    'X-Lawdit-Trial-Session': sessionId,
  })
}

async function readProblem(response: Response): Promise<PublicAnalysisProblem> {
  try {
    return await response.json() as PublicAnalysisProblem
  } catch {
    return { detail: response.statusText }
  }
}
