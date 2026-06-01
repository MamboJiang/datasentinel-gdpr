/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  authLoginUrlWithReturnTo,
  loadAuthProviders,
  loadAuthSession,
  logoutAuthSession,
  type AuthProviderOption,
  type AuthSession,
} from './authApi'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous' | 'unavailable'

type AuthContextValue = {
  enabled: boolean
  providers: AuthProviderOption[]
  session: AuthSession
  status: AuthStatus
  login: (provider: AuthProviderOption) => void
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const anonymousSession: AuthSession = { authenticated: false, user: null, expiresAt: null }
const AuthContext = createContext<AuthContextValue | null>(null)
const authGateEnabled = import.meta.env.VITE_LAWDIT_AUTH_GATE !== 'false'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [providers, setProviders] = useState<AuthProviderOption[]>([])
  const [session, setSession] = useState<AuthSession>(anonymousSession)
  const [status, setStatus] = useState<AuthStatus>(authGateEnabled ? 'loading' : 'authenticated')

  const refresh = useCallback(async () => {
    if (!authGateEnabled) {
      setStatus('authenticated')
      return
    }

    try {
      const [nextProviders, nextSession] = await Promise.all([
        loadAuthProviders(),
        loadAuthSession(),
      ])
      setProviders(nextProviders)
      setSession(nextSession)
      setStatus(nextSession.authenticated ? 'authenticated' : 'anonymous')
    } catch {
      setSession(anonymousSession)
      setStatus('unavailable')
    }
  }, [])

  const logout = useCallback(async () => {
    const nextSession = await logoutAuthSession()
    setSession(nextSession)
    setStatus('anonymous')
  }, [])

  useEffect(() => {
    if (!authGateEnabled) {
      return
    }

    let active = true

    Promise.all([loadAuthProviders(), loadAuthSession()])
      .then(([nextProviders, nextSession]) => {
        if (!active) {
          return
        }

        setProviders(nextProviders)
        setSession(nextSession)
        setStatus(nextSession.authenticated ? 'authenticated' : 'anonymous')
      })
      .catch(() => {
        if (!active) {
          return
        }

        setSession(anonymousSession)
        setStatus('unavailable')
      })

    return () => {
      active = false
    }
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    enabled: authGateEnabled,
    providers,
    session,
    status,
    login(provider) {
      if (provider.configured) {
        window.location.assign(authLoginUrlWithReturnTo(provider.loginUrl, window.location))
      }
    },
    logout,
    refresh,
  }), [logout, providers, refresh, session, status])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}
