import { afterEach, describe, expect, it, vi } from 'vitest'
import { analyzePublicFile, loadPublicAnalysisCapacity } from './publicAnalysisApi'

function envelope(data: unknown) {
  return {
    data,
    meta: {
      contractVersion: '0.1.0',
      generatedAt: '2026-06-01T00:00:00Z',
      traceId: 'trace_public_test',
      partial: false,
      warnings: [],
    },
  }
}

describe('public analysis API', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads real public capacity with the public analysis session header', async () => {
    const requests: { headers: Headers; path: string }[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      requests.push({ headers: init?.headers as Headers, path: String(input).replace('/api', '') })
      return new Response(JSON.stringify(envelope({
        maxActive: 10,
        activeAnalyses: 1,
        availableSlots: 9,
        waitingUsers: 0,
        queueMode: 'capacity_guard',
        userHasActiveAnalysis: false,
        userQueuePosition: null,
        fileSizeLimitBytes: 10485760,
      })), { headers: { 'Content-Type': 'application/json' }, status: 200 })
    }))

    const capacity = await loadPublicAnalysisCapacity('trial-session-a')

    expect(capacity.data.availableSlots).toBe(9)
    expect(requests).toHaveLength(1)
    expect(requests[0].path).toBe('/public-analysis/capacity')
    expect(requests[0].headers.get('X-Lawdit-Trial-Session')).toBe('trial-session-a')
  })

  it('uploads one file with FormData and leaves multipart content type to the browser', async () => {
    const requests: { body?: BodyInit | null; headers: Headers; path: string }[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      requests.push({ body: init?.body, headers: init?.headers as Headers, path: String(input).replace('/api', '') })
      return new Response(JSON.stringify(envelope({
        analysisId: 'analysis_test',
        status: 'completed',
        file: {
          name: 'note.txt',
          sizeBytes: 22,
          fileFormat: 'txt',
          extractionMethod: 'utf8_text',
          recognitionDifficulty: 'easy',
        },
        summary: {
          detectedSignalCount: 1,
          detectedTypes: [{ type: 'email', count: 1, highestConfidence: 0.91 }],
          riskLevel: 'medium',
          plainLanguageSummary: {
            headline: 'This txt file contains 1 email address signal.',
            explanation: 'lawdit found 1 redacted signal candidate that can identify, contact, or profile a person and should be checked by an accountable owner.',
            gdprRelevance: 'GDPR relevance: email address can identify or contact a person.',
            reviewFocus: 'Start with Line 1. Ask the source owner whether these signals are expected for this file.',
            detectedCategoryLabels: ['Email Address'],
            evidenceLocations: ['Line 1'],
          },
          reviewRecommendation: 'Review the matched evidence before deciding whether the file needs governed follow-up.',
          nextSteps: ['Assign an accountable owner to confirm whether the detected signal is expected.'],
          workflowReadiness: ['Redacted evidence is ready for human review.'],
          boundaryNotes: ['No Workspace source, finding, audit event, or deletion action is created from this upload.'],
          rawContentExposed: false,
          legalConclusionProvided: false,
          deletionAvailable: false,
        },
        analysisStages: [{ name: 'Signal detection', status: 'completed', description: '1 redacted signal candidate produced a medium review priority.' }],
        governanceBoundaries: ['Ten active public analyses across the API process.'],
        evidence: [{
          type: 'email',
          detector: 'email_pattern',
          confidence: 0.91,
          snippet: 'Email: [REDACTED_EMAIL]',
          locationLabel: 'Line 1',
          location: {
            format: 'text',
            anchorId: 'anchor_test_email',
            label: 'Line 1',
            rawContentExposed: false,
            selector: {
              type: 'textPosition',
              sourceStart: 7,
              sourceEnd: 23,
              lineNumber: 1,
              columnNumber: 8,
            },
          },
        }],
        warnings: [],
        capacity: {
          maxActive: 10,
          activeAnalyses: 0,
          availableSlots: 10,
          waitingUsers: 0,
          queueMode: 'capacity_guard',
          userHasActiveAnalysis: false,
          userQueuePosition: null,
          fileSizeLimitBytes: 10485760,
        },
      })), { headers: { 'Content-Type': 'application/json' }, status: 200 })
    }))

    const file = new File(['Email: user@example.org'], 'note.txt', { type: 'text/plain' })
    const result = await analyzePublicFile(file, 'trial-session-b')

    expect(result.data.summary.rawContentExposed).toBe(false)
    expect(result.data.summary.plainLanguageSummary?.headline).toContain('email address')
    expect(result.data.summary.plainLanguageSummary?.gdprRelevance).toContain('can identify or contact a person')
    expect(result.data.evidence[0].location?.rawContentExposed).toBe(false)
    expect(result.data.evidence[0].location?.selector?.lineNumber).toBe(1)
    expect(result.data.summary.nextSteps).toContain('Assign an accountable owner to confirm whether the detected signal is expected.')
    expect(result.data.analysisStages?.[0].name).toBe('Signal detection')
    expect(result.data.governanceBoundaries).toContain('Ten active public analyses across the API process.')
    expect(requests[0].path).toBe('/public-analysis/analyze')
    expect(requests[0].body).toBeInstanceOf(FormData)
    expect(requests[0].headers.get('X-Lawdit-Trial-Session')).toBe('trial-session-b')
    expect(requests[0].headers.has('Content-Type')).toBe(false)
  })
})
