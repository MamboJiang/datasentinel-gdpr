import { isSourceScanReady, type ScanType } from './scanProfiles'
import type { GovernanceConfig, Meta, Source } from '../types'

export function getSourceConnectionMessage(source: Source | undefined, governanceConfig: GovernanceConfig): string {
  if (!source) {
    return 'Source is not available.'
  }

  return isSourceScanReady(source, governanceConfig)
    ? `${source.name} is mock-ready for full scan.`
    : `${source.name} is not scan-ready in this P0 workflow.`
}

export function createPartialMeta(current: Meta, warnings: string[]): Meta {
  return {
    ...current,
    partial: true,
    warnings,
  }
}

export function clearPartialMeta(current: Meta): Meta {
  return { ...current, partial: false, warnings: [] }
}

export function calculateScannedGb(totalBytes: number, progress: number): number {
  return Number(((totalBytes * progress) / 1_000_000_000).toFixed(3))
}

export function normalizeScanType(value: string): ScanType {
  return value === 'delta' ? 'delta' : 'full'
}
