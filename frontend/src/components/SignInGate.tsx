import type { ReactNode } from 'react'
import { useAuth } from '../data/AuthContext'
import './SignInGate.css'

export function SignInGate({ children }: { children: ReactNode }) {
  const auth = useAuth()

  if (!auth.enabled || auth.status === 'authenticated') {
    return <>{children}</>
  }

  if (auth.status === 'loading') {
    return (
      <main className="signin-page">
        <section className="signin-panel" aria-labelledby="signin-title">
          <h1 className="signin-brand" id="signin-title">
            <BrandMark />
            <span>DataSentinel</span>
          </h1>
          <div className="signin-notice" role="status">
            Checking session.
          </div>
        </section>
      </main>
    )
  }

  const unavailable = auth.status === 'unavailable'
  const providers = auth.providers.filter((provider) => provider.provider === 'google' || provider.provider === 'github')

  return (
    <main className="signin-page">
      <section className="signin-panel" aria-labelledby="signin-title">
        <h1 className="signin-brand" id="signin-title">
          <BrandMark />
          <span>DataSentinel</span>
        </h1>

        <div className="signin-actions" aria-label="Sign in providers">
          {providers.map((provider) => (
            <button
              className="signin-button"
              disabled={!provider.configured}
              key={provider.provider}
              onClick={() => auth.login(provider)}
              type="button"
            >
              <ProviderLogo provider={provider.provider} />
              <span>Sign in with {provider.label}</span>
            </button>
          ))}
        </div>

        {unavailable ? (
          <div className="signin-notice" role="status">
            Server unavailable.
          </div>
        ) : null}

        {!unavailable && providers.some((provider) => !provider.configured) ? (
          <div className="signin-notice" role="status">
            Provider not configured.
          </div>
        ) : null}
      </section>
    </main>
  )
}

function BrandMark() {
  return (
    <svg aria-hidden="true" className="signin-brand-mark" viewBox="0 0 36 36">
      <circle cx="6" cy="6" r="3.4" />
      <circle cx="18" cy="6" r="3.4" />
      <circle cx="30" cy="6" r="3.4" />
      <circle cx="6" cy="18" r="3.4" />
      <circle cx="18" cy="18" r="3.4" />
      <circle cx="30" cy="18" r="3.4" />
      <circle cx="6" cy="30" r="3.4" />
      <circle cx="18" cy="30" r="3.4" />
      <circle cx="30" cy="30" r="3.4" />
    </svg>
  )
}

function ProviderLogo({ provider }: { provider: 'google' | 'github' }) {
  if (provider === 'github') {
    return (
      <svg aria-hidden="true" className="signin-provider-logo signin-provider-logo-github" viewBox="0 0 24 24">
        <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.1 3.29 9.42 7.86 10.95.58.1.79-.25.79-.56v-2.14c-3.2.7-3.87-1.36-3.87-1.36-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.04 1.76 2.71 1.25 3.37.96.1-.75.4-1.25.73-1.54-2.55-.29-5.23-1.28-5.23-5.68 0-1.25.45-2.28 1.19-3.08-.12-.29-.52-1.46.11-3.04 0 0 .97-.31 3.17 1.18A10.9 10.9 0 0 1 12 6.1c.98 0 1.95.13 2.87.39 2.2-1.49 3.17-1.18 3.17-1.18.63 1.58.23 2.75.11 3.04.74.8 1.19 1.83 1.19 3.08 0 4.41-2.69 5.38-5.25 5.67.41.36.78 1.06.78 2.13v3.16c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
      </svg>
    )
  }

  return (
    <svg aria-hidden="true" className="signin-provider-logo signin-provider-logo-google" viewBox="0 0 24 24">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.19 3.32v2.76h3.55c2.08-1.92 3.28-4.74 3.28-8.09Z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.55-2.76c-.98.66-2.23 1.06-3.73 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" fill="#34A853" />
      <path d="M5.84 14.11a6.61 6.61 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84Z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15A10.58 10.58 0 0 0 12 1 11 11 0 0 0 2.18 7.05l3.66 2.84C6.71 7.29 9.14 5.38 12 5.38Z" fill="#EA4335" />
    </svg>
  )
}
