import { describe, expect, it } from 'vitest'
import { buildEvidenceAnchors, buildPageRegionFocus } from './fileReviewEditorModel'
import type { Signal } from '../types'

describe('buildEvidenceAnchors', () => {
  it('uses backend PDF text-layer anchors without exposing raw values', () => {
    const signals: Signal[] = [{
      type: 'email',
      detector: 'email_label',
      confidence: 0.91,
      snippet: 'Email: [REDACTED_EMAIL]',
      evidenceAnchor: {
        anchorId: 'anchor_pdf_email',
        format: 'pdf_text_layer',
        label: 'Email',
        redactedText: 'Email: [REDACTED_EMAIL]',
        selector: {
          type: 'textPosition',
          start: 140,
          end: 164,
          page: 2,
          sourceStart: 14,
          sourceEnd: 38,
        },
        fallback: {
          label: 'Page 2',
          redactedText: 'Email: [REDACTED_EMAIL]',
        },
        rawContentExposed: false,
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)
    const serialized = JSON.stringify(anchor)

    expect(anchor.anchorId).toBe('anchor_pdf_email')
    expect(anchor.format).toBe('Pdf Text Layer')
    expect(anchor.locationLabel).toBe('Page 2')
    expect(anchor.selectorLabel).toBe('Page text 14-38')
    expect(anchor.redactedText).toBe('Email: [REDACTED_EMAIL]')
    expect(serialized).not.toContain('pdf.detail@example.org')
  })

  it('falls back to signal page and redacted snippet when an explicit anchor is absent', () => {
    const signals: Signal[] = [{
      type: 'phone_number',
      detector: 'phone_label',
      confidence: 0.84,
      snippet: 'Phone: [REDACTED_PHONE]',
      page: 3,
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.anchorId).toBe('phone_number-phone_label-0')
    expect(anchor.locationLabel).toBe('Page 3')
    expect(anchor.selectorLabel).toBe('Fallback selector')
    expect(anchor.redactedText).toBe('Phone: [REDACTED_PHONE]')
  })

  it('renders text-position offsets for non-PDF text streams', () => {
    const signals: Signal[] = [{
      type: 'person_name',
      detector: 'multilingual_person_label',
      confidence: 0.8,
      snippet: '姓名: [REDACTED_PERSON_NAME]',
      evidenceAnchor: {
        anchorId: 'anchor_text_name',
        format: 'text',
        label: 'Person Name',
        redactedText: '姓名: [REDACTED_PERSON_NAME]',
        selector: { type: 'textPosition', start: 3, end: 5 },
        fallback: { label: 'Line 1', redactedText: '姓名: [REDACTED_PERSON_NAME]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.locationLabel).toBe('Line 1')
    expect(anchor.selectorLabel).toBe('Text 3-5')
    expect(JSON.stringify(anchor)).not.toContain('王芳')
  })

  it('renders video frame OCR anchors as frame-local locations', () => {
    const signals: Signal[] = [{
      type: 'email',
      detector: 'video_frame_ocr',
      confidence: 0.87,
      snippet: 'Email: [REDACTED_EMAIL]',
      evidenceAnchor: {
        anchorId: 'anchor_video_frame_email',
        format: 'video_ocr',
        label: 'Email',
        redactedText: 'Email: [REDACTED_EMAIL]',
        selector: {
          type: 'textPosition',
          start: 10,
          end: 36,
          sourceStart: 10,
          sourceEnd: 36,
          page: 1,
          frameIndex: 1,
        },
        fallback: { label: 'Frame 1 OCR text', redactedText: 'Email: [REDACTED_EMAIL]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.format).toBe('Video Ocr')
    expect(anchor.locationLabel).toBe('Frame 1 OCR text')
    expect(anchor.selectorLabel).toBe('Page text 10-36')
    expect(JSON.stringify(anchor)).not.toContain('privacy.video@example.org')
  })

  it('renders table-cell selectors without raw cell values', () => {
    const signals: Signal[] = [{
      type: 'person_name',
      detector: 'person_label',
      confidence: 0.84,
      snippet: 'Name: [REDACTED_PERSON_NAME]',
      evidenceAnchor: {
        anchorId: 'anchor_xlsx_name',
        format: 'xlsx',
        label: 'Person Name',
        redactedText: 'Name: [REDACTED_PERSON_NAME]',
        selector: {
          type: 'tableCell',
          start: 6,
          end: 21,
          sourceStart: 0,
          sourceEnd: 15,
          row: 2,
          column: 2,
          columnLabel: 'B',
          sheetName: 'Sheet1',
        },
        fallback: { label: 'Sheet1 row 2 column B', redactedText: 'Name: [REDACTED_PERSON_NAME]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.locationLabel).toBe('Sheet1 row 2 column B')
    expect(anchor.selectorLabel).toBe('Sheet1 row 2 column B')
    expect(JSON.stringify(anchor)).not.toContain('Sophie de Vries')
  })

  it('renders structure-path selectors without raw document text', () => {
    const signals: Signal[] = [{
      type: 'person_name',
      detector: 'person_label',
      confidence: 0.84,
      snippet: 'Name: [REDACTED_PERSON_NAME]',
      evidenceAnchor: {
        anchorId: 'anchor_docx_name',
        format: 'docx',
        label: 'Person Name',
        redactedText: 'Name: [REDACTED_PERSON_NAME]',
        selector: {
          type: 'structurePath',
          start: 6,
          end: 19,
          sourceStart: 0,
          sourceEnd: 13,
          path: 'word/document.xml#paragraph:2',
          partName: 'word/document.xml',
          paragraphIndex: 2,
          blockLabel: 'DOCX paragraph 2',
        },
        fallback: { label: 'DOCX paragraph 2', redactedText: 'Name: [REDACTED_PERSON_NAME]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.locationLabel).toBe('DOCX paragraph 2')
    expect(anchor.selectorLabel).toBe('DOCX paragraph 2')
    expect(JSON.stringify(anchor)).not.toContain('Claire Martin')
  })

  it('renders JSON structure-path selectors without raw values', () => {
    const signals: Signal[] = [{
      type: 'person_name',
      detector: 'multilingual_label.zh.person_name',
      confidence: 0.84,
      snippet: '姓名: [REDACTED_PERSON_NAME]',
      evidenceAnchor: {
        anchorId: 'anchor_jsonl_name',
        format: 'jsonl',
        label: 'Person Name',
        redactedText: '姓名: [REDACTED_PERSON_NAME]',
        selector: {
          type: 'structurePath',
          start: 12,
          end: 14,
          sourceStart: 4,
          sourceEnd: 6,
          path: '/record[1]/field[1]/field[1]',
          recordIndex: 1,
          lineNumber: 1,
          fieldIndex: 1,
          blockLabel: 'JSONL record 1 field 1.1',
        },
        fallback: { label: 'JSONL record 1 field 1.1', redactedText: '姓名: [REDACTED_PERSON_NAME]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.locationLabel).toBe('JSONL record 1 field 1.1')
    expect(anchor.selectorLabel).toBe('JSONL record 1 field 1.1')
    expect(JSON.stringify(anchor)).not.toContain('王芳')
  })

  it('renders XML structure-path selectors without raw values', () => {
    const signals: Signal[] = [{
      type: 'phone_number',
      detector: 'multilingual_label.zh.phone_number',
      confidence: 0.84,
      snippet: '电话: [REDACTED_PHONE]',
      evidenceAnchor: {
        anchorId: 'anchor_xml_phone',
        format: 'xml',
        label: 'Phone Number',
        redactedText: '电话: [REDACTED_PHONE]',
        selector: {
          type: 'structurePath',
          start: 4,
          end: 16,
          sourceStart: 0,
          sourceEnd: 12,
          path: '/element[1]/element[1]/attribute[1]',
          elementIndex: 1,
          attributeIndex: 1,
          blockLabel: 'XML element 1.1 attribute 1',
        },
        fallback: { label: 'XML element 1.1 attribute 1', redactedText: '电话: [REDACTED_PHONE]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.locationLabel).toBe('XML element 1.1 attribute 1')
    expect(anchor.selectorLabel).toBe('XML element 1.1 attribute 1')
    expect(JSON.stringify(anchor)).not.toContain('+33123456789')
  })

  it('renders PDF page-region selectors without raw values', () => {
    const signals: Signal[] = [{
      type: 'email',
      detector: 'email_label',
      confidence: 0.91,
      snippet: 'Email: [REDACTED_EMAIL]',
      evidenceAnchor: {
        anchorId: 'anchor_pdf_region',
        format: 'pdf_text_layer',
        label: 'Email',
        redactedText: 'Email: [REDACTED_EMAIL]',
        selector: {
          type: 'textPosition',
          start: 20,
          end: 42,
          page: 1,
          sourceStart: 20,
          sourceEnd: 42,
          pageRegion: {
            x: 72.2,
            y: 720,
            width: 132.4,
            height: 12,
            unit: 'pt',
            origin: 'bottom_left',
            confidence: 'estimated',
          },
        },
        fallback: { label: 'Page 1', redactedText: 'Email: [REDACTED_EMAIL]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.locationLabel).toBe('Page 1')
    expect(anchor.selectorLabel).toBe('PDF region 72,720 132x12 pt')
    expect(anchor.pageRegionFocus?.kind).toBe('pdf')
    expect(anchor.pageRegionFocus?.boxStyle).toMatchObject({
      height: '1.5151515151515151%',
      left: '11.797385620915033%',
      top: '7.575757575757576%',
      width: '21.633986928104576%',
    })
    expect(JSON.stringify(anchor)).not.toContain('pdf.region@example.org')
  })

  it('renders OCR image-region selectors without raw values', () => {
    const signals: Signal[] = [{
      type: 'email',
      detector: 'email_regex',
      confidence: 0.88,
      snippet: 'Email: [REDACTED_EMAIL]',
      evidenceAnchor: {
        anchorId: 'anchor_ocr_region',
        format: 'image_ocr',
        label: 'Email',
        redactedText: 'Email: [REDACTED_EMAIL]',
        selector: {
          type: 'textPosition',
          start: 8,
          end: 33,
          sourceStart: 8,
          sourceEnd: 33,
          pageRegion: {
            x: 148,
            y: 44,
            width: 190,
            height: 22,
            pageWidth: 800,
            pageHeight: 600,
            unit: 'px',
            origin: 'top_left',
            confidence: 'ocr',
            ocrConfidence: 93.4,
          },
        },
        fallback: { label: 'Image OCR text', redactedText: 'Email: [REDACTED_EMAIL]' },
      },
    }]

    const [anchor] = buildEvidenceAnchors(signals)

    expect(anchor.locationLabel).toBe('Image OCR text')
    expect(anchor.selectorLabel).toBe('Image region 148,44 190x22 px')
    expect(anchor.pageRegionFocus?.kind).toBe('image')
    expect(anchor.pageRegionFocus?.boxStyle).toMatchObject({
      height: '3.6666666666666665%',
      left: '18.5%',
      top: '7.333333333333333%',
      width: '23.75%',
    })
    expect(JSON.stringify(anchor)).not.toContain('privacy.image@example.org')
  })

  it('normalizes bottom-left PDF and top-left OCR coordinates to the same focus style shape', () => {
    const pdfFocus = buildPageRegionFocus({
      x: 72,
      y: 720,
      width: 120,
      height: 12,
      pageWidth: 612,
      pageHeight: 792,
      unit: 'pt',
      origin: 'bottom_left',
    })
    const imageFocus = buildPageRegionFocus({
      x: 120,
      y: 36,
      width: 218,
      height: 20,
      pageWidth: 800,
      pageHeight: 600,
      unit: 'px',
      origin: 'top_left',
    })

    expect(pdfFocus?.kind).toBe('pdf')
    expect(pdfFocus?.frameStyle).toEqual({ aspectRatio: '612 / 792' })
    expect(pdfFocus?.boxStyle.top).toBe('7.575757575757576%')
    expect(imageFocus?.kind).toBe('image')
    expect(imageFocus?.frameStyle).toEqual({ aspectRatio: '800 / 600' })
    expect(imageFocus?.boxStyle.top).toBe('6%')
  })

})
