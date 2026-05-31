import { describe, expect, it } from 'vitest'
import { getInitialMockData } from './mockApi'

describe('getInitialMockData source review preview', () => {
  it('keeps source review preview anchors aligned with the assembled finding detail', () => {
    const data = getInitialMockData()
    const finding = data.findingDetails.finding_001

    expect(finding.sourceReviewPreview).toMatchObject({
      rawContentExposed: false,
      redactionMode: 'anchor_only',
      sourceName: finding.fileName,
    })
    expect(finding.sourceReviewPreview?.anchors?.length ?? 0).toBeGreaterThan(0)
    expect(finding.sourceReviewPreview?.contextWindows?.length).toBe(finding.signals?.length ?? 0)
    expect(finding.sourceReviewPreview?.anchors?.[0]).toMatchObject({
      anchorId: 'employee_id-employee_identifier_pattern-0',
      contextWindow: {
        redactedContext: 'Employee ID: [REDACTED_ID]',
        rawContentExposed: false,
      },
    })
    expect(data.findingDetail.sourceReviewPreview).toBe(finding.sourceReviewPreview)
  })
})
