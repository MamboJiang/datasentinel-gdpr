import { ArrowRight, CheckCircle2, Cloud, ExternalLink, RefreshCw, ShieldCheck, Unplug } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, PageHeader, SectionHeader, StatusBadge } from '../components/ui'
import { humanize } from '../components/formatters'
import { useAuth } from '../data/AuthContext'
import { disconnectGoogleDriveBinding, googleDriveBindingStartUrl } from '../data/authApi'
import { useData } from '../data/useData'
import {
  changelogItems,
  documentationMap,
  feedbackCategories,
  helpTopics,
  planBoundaries,
  sessionBoundaries,
} from '../data/sessionSimulation'
import './SupportPages.css'

export function AccountPage() {
  const { googleDriveBinding, permissionBoundary, meta, refreshGoogleDriveBinding, workspaceAdmin, workspaceDirectory } = useData()
  const { session } = useAuth()
  const user = session.user
  const [driveBusy, setDriveBusy] = useState(false)
  const [driveMessage, setDriveMessage] = useState<string | null>(null)
  const workspace = workspaceDirectory.workspaces.find((item) => item.workspaceId === workspaceDirectory.currentWorkspaceId)
    ?? workspaceAdmin.workspace
  const driveConnected = Boolean(googleDriveBinding?.connected)

  async function disconnectDriveBinding() {
    if (!window.confirm('Disconnect Google Drive from this lawdit account? Existing source registrations will stay, but scans will need a new binding or Picker authorization.')) {
      return
    }

    setDriveBusy(true)
    setDriveMessage(null)
    try {
      const result = await disconnectGoogleDriveBinding()
      await refreshGoogleDriveBinding()
      setDriveMessage(result.revoked ? 'Google Drive binding disconnected and provider token revocation was accepted.' : 'Google Drive binding disconnected locally.')
    } catch (error) {
      setDriveMessage(error instanceof Error ? error.message : 'Google Drive disconnect failed.')
    } finally {
      setDriveBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Account settings"
        description="Inspect the signed-in prelaunch account and the separate workflow permission boundary."
      />

      <div className="support-grid">
        <section className="panel">
          <SectionHeader title="Signed-in user" description="Provider identity is used for session access only." />
          <dl className="definition-list">
            <div><dt>Name</dt><dd>{user?.displayName ?? 'Not signed in'}</dd></div>
            <div><dt>Email</dt><dd>{user?.email ?? 'Email unavailable'}</dd></div>
            <div><dt>Provider</dt><dd>{user?.provider ? humanize(user.provider) : 'Unknown'}</dd></div>
            <div><dt>Session user ID</dt><dd>{user?.userId ?? 'Unavailable'}</dd></div>
            <div><dt>Contract</dt><dd>{meta.contractVersion}</dd></div>
          </dl>
        </section>

        <section className="panel">
          <SectionHeader title="Workspace" description="Workspace membership is separate from account sign-in." />
          <dl className="definition-list">
            <div><dt>Name</dt><dd>{workspace?.name ?? 'No Workspace membership'}</dd></div>
            <div><dt>Plan</dt><dd>{workspace?.plan ?? 'Invitation required'}</dd></div>
            <div><dt>Groups</dt><dd>{workspaceAdmin.currentMembership?.groupIds.map(humanize).join(', ') || 'None'}</dd></div>
            <div><dt>Pending invite links</dt><dd>{workspaceDirectory.pendingInvitations.length}</dd></div>
          </dl>
        </section>

        <section className="panel">
          <SectionHeader title="Google Drive binding" description="Personal Drive access is stored server-side for prelaunch scans." />
          <dl className="definition-list">
            <div><dt>Status</dt><dd>{driveConnected ? 'Connected' : 'Not connected'}</dd></div>
            <div><dt>Drive account</dt><dd>{googleDriveBinding?.email ?? googleDriveBinding?.displayName ?? 'Not connected'}</dd></div>
            <div><dt>Updated</dt><dd>{googleDriveBinding?.updatedAt ? humanizeDateTime(googleDriveBinding.updatedAt) : 'Unavailable'}</dd></div>
            <div><dt>Token boundary</dt><dd>{googleDriveBinding?.serverSideOnly ? 'Server-side only' : 'No provider token exposed'}</dd></div>
          </dl>
          <div className="support-actions">
            <Button
              disabled={!user || googleDriveBinding?.configured === false || driveBusy}
              icon={driveConnected ? RefreshCw : Cloud}
              onClick={() => window.location.assign(googleDriveBindingStartUrl())}
            >
              {driveConnected ? 'Change binding' : 'Connect Google Drive'}
            </Button>
            <Button disabled={!driveConnected || driveBusy} icon={Unplug} onClick={disconnectDriveBinding} variant="ghost">
              Disconnect
            </Button>
          </div>
          {googleDriveBinding?.configured === false ? (
            <p className="form-error">Google OAuth client credentials are not configured on this host.</p>
          ) : null}
          {driveMessage ? (
            <p className="support-success" role="status">
              <CheckCircle2 aria-hidden="true" size={16} />
              {driveMessage}
            </p>
          ) : null}
        </section>
      </div>

      <section className="panel support-section">
        <SectionHeader title="Permission boundary" description="Allowed and denied actions remain visible before review decisions." />
        <div className="permission-columns">
          <div>
            <h3><ShieldCheck aria-hidden="true" size={16} /> Allowed actions</h3>
            {(permissionBoundary.allowedActions ?? []).map((action) => <span className="permission-chip permission-allowed" key={action}>{humanize(action)}</span>)}
          </div>
          <div>
            <h3><ShieldCheck aria-hidden="true" size={16} /> Denied actions</h3>
            {(permissionBoundary.deniedActions ?? []).map((action) => (
              <article className="denied-action" key={action.action}>
                <strong>{humanize(action.action)}</strong>
                <p>{action.reason}</p>
              </article>
            ))}
          </div>
        </div>
        <div className="visible-scopes">
          <ShieldCheck aria-hidden="true" size={16} />
          <span>Visible scopes: {permissionBoundary.visibleScopes.map(humanize).join(', ')}</span>
        </div>
      </section>

      <section className="panel support-section">
        <SectionHeader title="Workspace permission boundary" description="Workspace admin powers are granted only through Workspace groups." />
        <div className="permission-columns">
          <div>
            <h3><ShieldCheck aria-hidden="true" size={16} /> Allowed workspace actions</h3>
            {(workspaceAdmin.permissionBoundary.allowedActions ?? []).map((action) => <span className="permission-chip permission-allowed" key={action}>{humanize(action)}</span>)}
          </div>
          <div>
            <h3><ShieldCheck aria-hidden="true" size={16} /> Denied workspace actions</h3>
            {(workspaceAdmin.permissionBoundary.deniedActions ?? []).map((action) => (
              <article className="denied-action" key={action.action}>
                <strong>{humanize(action.action)}</strong>
                <p>{action.reason}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}

function humanizeDateTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function FeedbackPage() {
  const [category, setCategory] = useState(feedbackCategories[0])
  const [details, setDetails] = useState('')
  const [submitted, setSubmitted] = useState(false)

  return (
    <>
      <PageHeader
        eyebrow="Local feedback"
        title="Feedback"
        description="Capture a prototype note without sending data to an external service."
      />

      <section className="panel support-form-panel">
        <form
          className="support-form"
          onSubmit={(event) => {
            event.preventDefault()
            setSubmitted(true)
            setDetails('')
          }}
        >
          <label className="form-field">
            <span>Category</span>
            <select onChange={(event) => setCategory(event.target.value)} value={category}>
              {feedbackCategories.map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <label className="form-field">
            <span>Feedback note</span>
            <textarea
              onChange={(event) => {
                setDetails(event.target.value)
                setSubmitted(false)
              }}
              placeholder="Describe what should be clearer or safer in the prototype."
              rows={6}
              value={details}
            />
          </label>
          <div className="dialog-notice">
            <ShieldCheck aria-hidden="true" size={17} />
            <span>Do not paste raw sensitive content. This form stores no server record in P0.</span>
          </div>
          <div className="support-actions">
            <Button disabled={details.trim().length < 8} type="submit">Save local note</Button>
          </div>
          {submitted ? (
            <p className="support-success" role="status">
              <CheckCircle2 aria-hidden="true" size={16} />
              Local feedback note saved for this prototype session.
            </p>
          ) : null}
        </form>
      </section>
    </>
  )
}

export function ChangelogPage() {
  return (
    <>
      <PageHeader eyebrow="Prototype history" title="Changelog" description="Recent P0 implementation milestones for reviewers." />
      <section className="panel">
        <div className="support-list">
          {changelogItems.map((item) => (
            <article className="support-row" key={item.title}>
              <CheckCircle2 aria-hidden="true" size={17} />
              <div>
                <strong>{item.title}</strong>
                <p>{item.description}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}

export function HelpPage() {
  return (
    <>
      <PageHeader eyebrow="Workflow help" title="Help" description="Task-oriented guidance for the internal console." />
      <div className="support-grid support-grid-three">
        {helpTopics.map((topic) => (
          <Link className="support-card" key={topic.title} to={topic.path}>
            <strong>{topic.title}</strong>
            <p>{topic.description}</p>
            <span>Open surface <ArrowRight aria-hidden="true" size={14} /></span>
          </Link>
        ))}
      </div>
    </>
  )
}

export function DocsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Repository docs"
        title="Docs"
        description="Map of the local project documents that define the contract-first workflow."
      />
      <section className="panel">
        <div className="support-list">
          {documentationMap.map((doc) => (
            <article className="support-row" key={doc.reference}>
              <ExternalLink aria-hidden="true" size={17} />
              <div>
                <strong>{doc.title}</strong>
                <p>{doc.description}</p>
                <code>{doc.reference}</code>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}

export function PlatformStatusPage() {
  const { meta, scan, sources, evaluation } = useData()
  const resourceIntensity = evaluation.resourceIntensity ?? {}
  const modelCalls = resourceIntensity.modelCalls ?? 0
  const estimatedCostUsd = resourceIntensity.estimatedCostUsd ?? 0

  return (
    <>
      <PageHeader
        eyebrow="Runtime status"
        title="Platform status"
        description="Health indicators for the prelaunch runtime. This is not production monitoring."
      />
      <div className="support-grid support-grid-three">
        <article className="support-card">
          <strong>Frontend runtime</strong>
          <p>Vite app loaded and ready to request the project API.</p>
          <StatusBadge value="completed" />
        </article>
        <article className="support-card">
          <strong>API contract</strong>
          <p>Contract {meta.contractVersion} · trace {meta.traceId}</p>
          <StatusBadge value={meta.partial ? 'warning' : 'completed'} />
        </article>
        <article className="support-card">
          <strong>Latest scan</strong>
          <p>{scan.scanId} · {humanize(scan.scanType)} · {Math.round(scan.progress * 100)}%</p>
          <StatusBadge value={scan.status} />
        </article>
      </div>
      <section className="panel support-section">
        <SectionHeader title="Source readiness" />
        <div className="support-list">
          {sources.map((source) => (
            <article className="support-row" key={source.sourceId}>
              <ShieldCheck aria-hidden="true" size={17} />
              <div>
                <strong>{source.name}</strong>
                <p>{source.rootLabel}</p>
              </div>
              <StatusBadge value={source.status} />
            </article>
          ))}
        </div>
        <div className="visible-scopes">
          <ShieldCheck aria-hidden="true" size={16} />
          <span>Resource intensity: {modelCalls} model calls · ${estimatedCostUsd.toFixed(2)} estimated paid-service cost.</span>
        </div>
      </section>
    </>
  )
}

export function PlanPage() {
  return (
    <>
      <PageHeader
        eyebrow="Prototype boundary"
        title="Prototype plan"
        description="The account menu exposes plan context without enabling billing, procurement, or production tenant onboarding."
      />
      <section className="panel">
        <div className="support-list">
          {planBoundaries.map((boundary) => (
            <article className="support-row" key={boundary}>
              <ShieldCheck aria-hidden="true" size={17} />
              <div>
                <strong>{boundary}</strong>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}

export function SessionBoundaryPage() {
  const { logout, session } = useAuth()

  return (
    <>
      <PageHeader
        eyebrow="Session"
        title="Session boundary"
        description="Sign out clears the lawdit session cookie. Provider revocation remains managed by Google or GitHub."
      />
      <section className="panel">
        <div className="support-list">
          {sessionBoundaries.map((boundary) => (
            <article className="support-row" key={boundary}>
              <ShieldCheck aria-hidden="true" size={17} />
              <div>
                <strong>{boundary}</strong>
              </div>
            </article>
          ))}
        </div>
        <div className="support-actions">
          {session.authenticated ? <Button onClick={() => void logout()} variant="secondary">Log out</Button> : null}
          <Link className="button button-secondary" to="/">Open homepage</Link>
          <Link className="button button-primary" to="/dashboard">Return to dashboard</Link>
        </div>
      </section>
    </>
  )
}
