import { describe, expect, it } from 'vitest'
import { attachPreviewContextWindows, buildEvidenceAnchors, buildPreviewPageRegionFocus, buildSourcePreviewSummary } from './fileReviewEditorModel'
import type { SourceReviewPreview } from '../types'

describe('source review preview package', () => {
  it('drives region focus from backend preview data without raw values', () => {
    const region = {
      x: 144,
      y: 88,
      width: 224,
      height: 24,
      pageWidth: 1654,
      pageHeight: 2339,
      unit: 'px',
      origin: 'top_left',
      confidence: 'ocr',
      ocrConfidence: 90.1,
    }
    const preview: SourceReviewPreview = {
      sourcePreviewId: 'source_preview_123',
      sourceName: 'scan.pdf',
      fileFormat: 'pdf_ocr',
      extractionMethod: 'pdf_page_image_ocr',
      recognitionDifficulty: 'hard',
      redactionMode: 'anchor_only',
      rawContentExposed: false,
      pageImagesExposed: false,
      anchors: [{
        anchorId: 'anchor_ocr_region',
        label: 'Email',
        format: 'pdf_ocr',
        redactedText: 'Email: [REDACTED_EMAIL]',
        fallbackLabel: 'Page 1',
        contextWindow: {
          anchorId: 'anchor_ocr_region',
          redactedContext: 'Contact Email: [REDACTED_EMAIL]',
          contextStart: 0,
          contextEnd: 42,
          highlightStart: 15,
          highlightEnd: 31,
          redactionMode: 'signal_span_context',
          rawContentExposed: false,
        },
        selector: { type: 'textPosition', sourceStart: 8, sourceEnd: 33, page: 1, pageRegion: region },
        rawContentExposed: false,
      }],
      contextWindows: [{
        anchorId: 'anchor_ocr_region',
        redactedContext: 'Contact Email: [REDACTED_EMAIL]',
        contextStart: 0,
        contextEnd: 42,
        highlightStart: 15,
        highlightEnd: 31,
        redactionMode: 'signal_span_context',
        rawContentExposed: false,
      }],
      pages: [{
        page: 1,
        label: 'Page 1',
        coordinateSystem: 'image_pixels_top_left',
        pageImageExposed: false,
        regions: [{
          anchorId: 'anchor_ocr_region',
          label: 'Email',
          redactedText: 'Email: [REDACTED_EMAIL]',
          region,
          rawContentExposed: false,
        }],
      }],
      textRanges: [{}],
      tableCells: [],
      structureBlocks: [],
      warnings: [],
    }

    const summary = buildSourcePreviewSummary(preview)
    const focus = buildPreviewPageRegionFocus(preview, 'anchor_ocr_region')
    const anchors = attachPreviewContextWindows(buildEvidenceAnchors([{
      type: 'email',
      detector: 'email_label',
      confidence: 0.91,
      snippet: 'Email: [REDACTED_EMAIL]',
      evidenceAnchor: {
        anchorId: 'anchor_ocr_region',
        format: 'pdf_ocr',
        label: 'Email',
        redactedText: 'Email: [REDACTED_EMAIL]',
        selector: { type: 'textPosition', sourceStart: 8, sourceEnd: 33, page: 1, pageRegion: region },
        fallback: { label: 'Page 1', redactedText: 'Email: [REDACTED_EMAIL]' },
      },
    }]), preview)
    const serialized = JSON.stringify({ summary, focus, preview, anchors })

    expect(summary).toMatchObject({
      anchorCount: 1,
      formatLabel: 'Pdf Ocr',
      pageCount: 1,
      rawBoundaryLabel: 'Raw boundary sealed',
      redactionLabel: 'Anchor Only',
    })
    expect(focus?.kind).toBe('image')
    expect(focus?.frameStyle).toEqual({ aspectRatio: '1654 / 2339' })
    expect(anchors[0].contextWindow?.redactedContext).toBe('Contact Email: [REDACTED_EMAIL]')
    expect(serialized).not.toContain('preview.ocr@example.org')
  })
})
