import type { Finding, FindingSummary } from '../types'

type FindingSourceInput = Pick<FindingSummary, 'sourcePath'> & Pick<Finding, 'file'>

export function safeFindingSourceLabel(finding: FindingSourceInput): string {
  const sourceName = finding.file?.sourceName?.trim()
  const hiddenLabel = sourceName || 'Source reference hidden'
  const sourcePath = finding.sourcePath?.trim()

  if (!sourcePath) {
    return hiddenLabel
  }

  if (isExternalUrl(sourcePath) || isAbsoluteFilePath(sourcePath) || isOpaqueSourceReference(sourcePath)) {
    return hiddenLabel
  }

  return sourcePath
}

function isExternalUrl(value: string): boolean {
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

function isAbsoluteFilePath(value: string): boolean {
  return value.startsWith('/') || value.startsWith('~/') || /^[A-Za-z]:[\\/]/.test(value)
}

function isOpaqueSourceReference(value: string): boolean {
  return value.startsWith('source_reference:')
}
