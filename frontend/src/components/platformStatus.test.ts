import { describe, expect, it } from 'vitest'
import { getPlatformStatusView } from './platformStatus'

describe('platform status view copy', () => {
  it('shows a connected server state', () => {
    expect(getPlatformStatusView('connected')).toEqual({
      label: 'Server connected',
      tone: 'connected',
    })
  })

  it('shows a disconnected server state', () => {
    expect(getPlatformStatusView('disconnected')).toEqual({
      label: 'Server disconnected',
      tone: 'disconnected',
    })
  })

  it('shows the initial server check state', () => {
    expect(getPlatformStatusView('checking')).toEqual({
      label: 'Checking server',
      tone: 'checking',
    })
  })
})
