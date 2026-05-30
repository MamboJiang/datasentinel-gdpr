export function humanize(value?: string | null) {
  if (!value) {
    return 'Unknown'
  }

  return value
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function formatDate(value?: string | null) {
  if (!value) {
    return 'Not available'
  }

  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function formatBytes(bytes?: number) {
  if (typeof bytes !== 'number') {
    return 'Not available'
  }

  if (bytes < 1_000_000) {
    return `${Math.round(bytes / 1_000)} KB`
  }

  return `${(bytes / 1_000_000).toFixed(1)} MB`
}
