import { describe, expect, it } from 'vitest'
import { ApiRequestError } from './serverApi'
import { canUseLocalFallback, shouldUseLocalFallback } from './serverRefresh'

describe('server refresh fallback policy', () => {
  it('allows local mock fallback only for transport outages with explicit local mocks enabled', () => {
    const transportError = new TypeError('Failed to fetch')
    const apiRejection = new ApiRequestError('Google Drive authorization is required.', 409, {
      code: 'command-rejected',
      detail: 'Google Drive authorization is required.',
      title: 'Command rejected',
    })

    expect(shouldUseLocalFallback(transportError)).toBe(true)
    expect(canUseLocalFallback(transportError, true)).toBe(true)
    expect(canUseLocalFallback(transportError, false)).toBe(false)
    expect(shouldUseLocalFallback(apiRejection)).toBe(false)
    expect(canUseLocalFallback(apiRejection, true)).toBe(false)
  })
})
