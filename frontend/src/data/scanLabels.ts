export function formatScanType(scanType: string): string {
  return scanType === 'full' ? 'Full' : 'Delta'
}
