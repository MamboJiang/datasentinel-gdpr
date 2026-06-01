import { describe, expect, it } from 'vitest'
import { authLoginUrlWithReturnTo } from './authApi'

describe('auth login return path', () => {
  it('keeps the current finding deep link through the backend login URL', () => {
    expect(authLoginUrlWithReturnTo('/api/auth/login/google', {
      hash: '#evidence',
      origin: 'https://founder-force.uk',
      pathname: '/findings/finding_001',
      search: '?tab=source',
    } as Location)).toBe('/api/auth/login/google?returnTo=%2Ffindings%2Ffinding_001%3Ftab%3Dsource%23evidence')
  })

  it('does not send API routes as frontend return targets', () => {
    expect(authLoginUrlWithReturnTo('/api/auth/login/google', {
      hash: '',
      origin: 'https://founder-force.uk',
      pathname: '/api/findings',
      search: '',
    } as Location)).toBe('/api/auth/login/google')

    expect(authLoginUrlWithReturnTo('/api/auth/login/google', {
      hash: '',
      origin: 'https://founder-force.uk',
      pathname: '/api',
      search: '',
    } as Location)).toBe('/api/auth/login/google')
  })
})
