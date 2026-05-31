import { describe, expect, it } from 'vitest'
import { safeFindingSourceLabel } from './findingDisplay'

describe('safeFindingSourceLabel', () => {
  it('hides external source URLs while keeping the source name', () => {
    expect(safeFindingSourceLabel({
      sourcePath: 'https://drive.google.com/file/d/file-id/view?usp=drivesdk',
      file: { sourceName: 'GDPR data samples' },
    })).toBe('GDPR data samples')
  })

  it('hides absolute local paths', () => {
    expect(safeFindingSourceLabel({
      sourcePath: '/Users/example/private/source/Expense_Report.pdf',
      file: { sourceName: 'Local import' },
    })).toBe('Local import')
  })

  it('keeps non-sensitive relative references', () => {
    expect(safeFindingSourceLabel({
      sourcePath: 'samples/Expense_Report.pdf',
    })).toBe('samples/Expense_Report.pdf')
  })

  it('hides opaque backend source references behind the source name', () => {
    expect(safeFindingSourceLabel({
      sourcePath: 'source_reference:abc123',
      file: { sourceName: 'Drive source' },
    })).toBe('Drive source')
  })
})
