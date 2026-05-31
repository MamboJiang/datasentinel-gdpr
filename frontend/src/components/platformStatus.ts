import type { ServerConnectionStatus } from '../data/DataContext'

export type PlatformStatusView = {
  label: string
  tone: ServerConnectionStatus
}

export function getPlatformStatusView(status: ServerConnectionStatus): PlatformStatusView {
  switch (status) {
    case 'connected':
      return { label: 'Server connected', tone: 'connected' }
    case 'disconnected':
      return { label: 'Server disconnected', tone: 'disconnected' }
    case 'checking':
      return { label: 'Checking server', tone: 'checking' }
  }
}
