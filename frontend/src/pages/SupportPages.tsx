import { ArrowRight, CheckCircle2, ExternalLink, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, PageHeader, SectionHeader, StatusBadge } from '../components/ui'
import { humanize } from '../components/formatters'
import { useData } from '../data/useData'
import {
  accountSimulation,
  changelogItems,
  documentationMap,
  feedbackCategories,
  helpTopics,
  planBoundaries,
  sessionBoundaries,
  workspaceSimulation,
} from '../data/sessionSimulation'
import './SupportPages.css'

export function AccountPage() {
  const { permissionBoundary, meta } = useData()

  return (
    <>
      <PageHeader
        eyebrow="Account simulation"
        title="Account settings"
        description="Inspect the seeded demo actor used by the P0 console. This is not production authentication."
      />

      <div className="support-grid">
        <section className="panel">
          <SectionHeader title="Actor" description="Static demo identity for review and permission-boundary simulation." />
          <dl className="definition-list">
            <div><dt>Name</dt><dd>{accountSimulation.name}</dd></div>
            <div><dt>Email</dt><dd>{accountSimulation.email}</dd></div>
            <div><dt>Actor ID</dt><dd>{permissionBoundary.actorId || accountSimulation.actorId}</dd></div>
            <div><dt>Contract</dt><dd>{meta.contractVersion}</dd></div>
          </dl>
        </section>

        <section className="panel">
          <SectionHeader title="Workspace" description="The current workspace is mock-backed and local to the prototype." />
          <dl className="definition-list">
            <div><dt>Name</dt><dd>{workspaceSimulation.name}</dd></div>
            <div><dt>Plan</dt><dd>{workspaceSimulation.plan}</dd></div>
            <div><dt>Scope</dt><dd>{workspaceSimulation.description}</dd></div>
          </dl>
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
    </>
  )
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
        eyebrow="Mock-backed status"
        title="Platform status"
        description="Local health indicators for the prototype runtime. This is not production monitoring."
      />
      <div className="support-grid support-grid-three">
        <article className="support-card">
          <strong>Frontend runtime</strong>
          <p>Vite app loaded and rendering from local mock state.</p>
          <StatusBadge value="completed" />
        </article>
        <article className="support-card">
          <strong>Mock contract</strong>
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
        description="The account menu exposes plan context without enabling billing, procurement, or production onboarding."
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
  return (
    <>
      <PageHeader
        eyebrow="Session simulation"
        title="Session boundary"
        description="P0 uses a seeded actor instead of production authentication."
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
          <Link className="button button-secondary" to="/">Open homepage</Link>
          <Link className="button button-primary" to="/dashboard">Return to dashboard</Link>
        </div>
      </section>
    </>
  )
}
