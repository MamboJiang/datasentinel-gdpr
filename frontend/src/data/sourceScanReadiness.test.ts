import { describe, expect, it } from 'vitest'
import type { GovernanceConfig, Source } from '../types'
import { canStartSourceScan, sourceDisplayStatus, sourceScanBlockReason } from './sourceScanReadiness'

const governanceConfig = {
  sourceAdapters: [
    { sourceType: 'google_drive_selection', status: 'connected' },
    { sourceType: 'remote_file_link', status: 'connected' },
  ],
} as GovernanceConfig

function source(input: Partial<Source>): Source {
  return {
    sourceId: input.sourceId ?? 'source_1',
    name: input.name ?? 'Source',
    sourceType: input.sourceType ?? 'remote_file_link',
    status: input.status ?? 'connected',
    ...input,
  }
}

describe('source scan readiness', () => {
  it('requires a runtime Picker token or account binding for Google Drive scans', () => {
    const driveSource = source({ sourceId: 'source_drive', sourceType: 'google_drive_selection', status: 'authorization_required' })

    expect(canStartSourceScan(driveSource, governanceConfig, [])).toBe(false)
    expect(sourceScanBlockReason(driveSource, governanceConfig, [])).toBe('Google Drive scan requires a connected account binding or Picker authorization')
    expect(canStartSourceScan(driveSource, governanceConfig, ['source_drive'])).toBe(true)
    expect(canStartSourceScan(driveSource, governanceConfig, [], true)).toBe(true)
    expect(sourceDisplayStatus(driveSource, ['source_drive'])).toBe('connected')
    expect(sourceDisplayStatus(driveSource, [], true)).toBe('connected')
    expect(sourceDisplayStatus(driveSource, [])).toBe('authorization_required')
  })

  it('allows connected non-Drive sources without runtime authorization', () => {
    expect(canStartSourceScan(source({ sourceId: 'source_remote' }), governanceConfig, [])).toBe(true)
  })
})
