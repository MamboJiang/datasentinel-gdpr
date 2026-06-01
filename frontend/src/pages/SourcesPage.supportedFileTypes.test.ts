import { describe, expect, it } from 'vitest'
import {
  SUPPORTED_FILE_TYPES,
  SUPPORTED_FILE_TYPES_DESCRIPTION,
  SUPPORTED_FILE_TYPES_NOTE,
} from './sourceSupportContent'

describe('Sources supported file types', () => {
  it('keeps the public support list aligned with final engine formats', () => {
    expect(SUPPORTED_FILE_TYPES).toEqual([
      'TXT',
      'UTF-16 text',
      'Suffixless text/config',
      'CSV',
      'TSV',
      'JSON',
      'JSONL/NDJSON',
      'Markdown',
      'LOG',
      'XML',
      'HTML/HTM',
      'RTF',
      'PDF text layer',
      'DOCX',
      'XLSX',
      'PPTX',
      'DOC/XLS/PPT legacy Office text',
      'ODT',
      'ODS',
      'ODP',
      'EML email',
      'ZIP archives',
      'PDF image OCR',
      'PNG/JPG image OCR',
      'TIFF/BMP/WEBP image OCR',
      'VTT/SRT video transcripts',
      'MP4/MOV/M4V/MKV/WEBM/AVI video frame OCR',
      'Google Docs export',
      'Google Sheets export',
      'Google Slides export',
    ])
  })

  it('does not describe current OCR-backed formats as prelaunch-deferred', () => {
    expect(SUPPORTED_FILE_TYPES_DESCRIPTION).toBe('Core scanners read these formats during scan execution.')
    expect(SUPPORTED_FILE_TYPES_NOTE).toContain('host-local OCR tools')
    expect(SUPPORTED_FILE_TYPES_NOTE).toContain('FFmpeg')
    expect(SUPPORTED_FILE_TYPES_NOTE).toContain('LibreOffice')
    expect(`${SUPPORTED_FILE_TYPES_DESCRIPTION} ${SUPPORTED_FILE_TYPES_NOTE}`).not.toContain('prelaunch scanners')
    expect(`${SUPPORTED_FILE_TYPES_DESCRIPTION} ${SUPPORTED_FILE_TYPES_NOTE}`).not.toContain('OCR-deferred or unsupported')
  })
})
