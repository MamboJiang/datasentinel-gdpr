export type AuthProviderOption = {
  provider: 'google' | 'github'
  label: string
  configured: boolean
  loginUrl: string
}

export type AuthUser = {
  userId: string
  provider: 'google' | 'github'
  providerSubject: string
  displayName: string
  email?: string | null
  avatarUrl?: string | null
}

export type AuthSession = {
  authenticated: boolean
  user?: AuthUser | null
  expiresAt?: string | null
}

export type GoogleDriveBinding = {
  connected: boolean
  configured: boolean
  provider: 'google_drive'
  email?: string | null
  displayName?: string | null
  avatarUrl?: string | null
  scopes: string[]
  connectedAt?: string | null
  updatedAt?: string | null
  tokenRefreshAvailable?: boolean
  serverSideOnly?: boolean
  revocationAttempted?: boolean
  revoked?: boolean
}

export type GoogleDrivePickerToken = {
  accessToken: string
  provider: 'google_drive'
  scopes: string[]
  source: 'account_binding'
  tokenType: string
}

type ApiEnvelope<T> = {
  data: T
}

const apiBase = (import.meta.env.VITE_LAWDIT_API_BASE ?? '/api').replace(/\/$/, '')

export async function loadAuthProviders(): Promise<AuthProviderOption[]> {
  const envelope = await authRequest<AuthProviderOption[]>('/auth/providers')
  return envelope.data
}

export async function loadAuthSession(): Promise<AuthSession> {
  const envelope = await authRequest<AuthSession>('/auth/session')
  return envelope.data
}

export async function logoutAuthSession(): Promise<AuthSession> {
  const envelope = await authRequest<AuthSession>('/auth/logout', { method: 'POST' })
  return envelope.data
}

export async function loadGoogleDriveBinding(): Promise<GoogleDriveBinding> {
  const envelope = await authRequest<GoogleDriveBinding>('/integrations/google-drive/binding')
  return envelope.data
}

export async function disconnectGoogleDriveBinding(): Promise<GoogleDriveBinding> {
  const envelope = await authRequest<GoogleDriveBinding>('/integrations/google-drive/binding', { method: 'DELETE' })
  return envelope.data
}

export async function loadGoogleDrivePickerToken(): Promise<GoogleDrivePickerToken> {
  const envelope = await authRequest<GoogleDrivePickerToken>('/integrations/google-drive/picker-token', { method: 'POST' })
  return envelope.data
}

export function googleDriveBindingStartUrl(): string {
  return `${apiBase}/integrations/google-drive/bind/start`
}

export function authLoginUrlWithReturnTo(loginUrl: string, location: Pick<Location, 'hash' | 'origin' | 'pathname' | 'search'>): string {
  const target = new URL(loginUrl, location.origin)
  const returnTo = `${location.pathname}${location.search}${location.hash}`
  if (isSafeAppReturnPath(returnTo)) {
    target.searchParams.set('returnTo', returnTo)
  }
  return `${target.pathname}${target.search}${target.hash}`
}

async function authRequest<T>(path: string, init: RequestInit = {}): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json, application/problem+json',
      ...(init.headers ?? {}),
    },
  })

  if (!response.ok) {
    throw new Error(`Auth request failed with ${response.status}`)
  }

  return response.json() as Promise<ApiEnvelope<T>>
}

function isSafeAppReturnPath(value: string) {
  return value.startsWith('/')
    && !value.startsWith('//')
    && !value.startsWith('/api/')
    && !value.includes('\r')
    && !value.includes('\n')
}
