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

type ApiEnvelope<T> = {
  data: T
}

const apiBase = (import.meta.env.VITE_DATASENTINEL_API_BASE ?? '/api').replace(/\/$/, '')

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
