import { GitBranch, KeyRound, ShieldCheck } from 'lucide-react'
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
        <section className="signin-panel">
          <KeyRound aria-hidden="true" size={24} />
          <h1>Checking session</h1>
          <p>DataSentinel is verifying the prelaunch account session.</p>
        </section>
      </main>
    )
  }

  const unavailable = auth.status === 'unavailable'

  return (
    <main className="signin-page">
      <section className="signin-panel" aria-labelledby="signin-title">
        <div className="signin-mark" aria-hidden="true">
          <ShieldCheck size={24} />
        </div>
        <p className="eyebrow">Prelaunch access</p>
        <h1 id="signin-title">Sign in to DataSentinel</h1>
        <p>
          Use a configured Google or GitHub account to enter the privacy operations workspace.
          Provider tokens stay on the server; the browser receives only a DataSentinel session cookie.
        </p>

        <div className="signin-actions">
          {auth.providers.map((provider) => (
            <button
              className="signin-button"
              disabled={!provider.configured}
              key={provider.provider}
              onClick={() => auth.login(provider)}
              type="button"
            >
              {provider.provider === 'github' ? <GitBranch aria-hidden="true" size={18} /> : <KeyRound aria-hidden="true" size={18} />}
              <span>Continue with {provider.label}</span>
            </button>
          ))}
        </div>

        {unavailable ? (
          <div className="signin-notice" role="status">
            The API server is unavailable. Start the backend before entering the console.
          </div>
        ) : null}

        {!unavailable && auth.providers.some((provider) => !provider.configured) ? (
          <div className="signin-notice" role="status">
            A disabled provider is missing server-side client credentials or the session secret.
          </div>
        ) : null}
      </section>
    </main>
  )
}
