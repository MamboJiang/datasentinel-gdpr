const workflowSteps = [
  {
    label: '01',
    title: 'Open the console',
    body: 'Sign in when required, confirm your Workspace, and check which actions are allowed before you start.',
    href: '/dashboard',
  },
  {
    label: '02',
    title: 'Register a source',
    body: 'Use a controlled sample source, safe HTTPS file link, Google Drive Picker selection, or host-allowed local source.',
    href: '/docs/sources',
  },
  {
    label: '03',
    title: 'Run a full scan',
    body: 'Start from a ready source and watch pipeline stages, warnings, scan volume, and review backlog.',
    href: '/docs/dashboard-and-scans',
  },
  {
    label: '04',
    title: 'Review findings',
    body: 'Inspect redacted evidence, owner routing, retention context, denied actions, and required reasons.',
    href: '/docs/findings-and-review',
  },
]

const surfaceCards = [
  {
    title: 'Sources',
    eyebrow: 'Prepare input',
    body: 'Add supported sources and understand readiness, format limits, token boundaries, and source-registration removal.',
    href: '/docs/sources',
    accent: 'blue',
  },
  {
    title: 'Findings and Review',
    eyebrow: 'Make decisions',
    body: 'Use evidence cards and review support to record accountable human decisions without exposing raw content.',
    href: '/docs/findings-and-review',
    accent: 'green',
  },
  {
    title: 'Audit and Evaluation',
    eyebrow: 'Prove the workflow',
    body: 'Confirm scan/review events, quality metrics, reproducibility, throughput, and resource intensity.',
    href: '/docs/audit-and-evaluation',
    accent: 'amber',
  },
  {
    title: 'Safety Boundaries',
    eyebrow: 'Stay inside P0',
    body: 'Review no legal advice, no full-compliance claim, simulated deletion, redaction, and optional AI limits.',
    href: '/docs/safety-and-boundaries',
    accent: 'red',
  },
]

const visualTourCards = [
  {
    title: 'Dashboard',
    body: 'Check scan coverage, review focus, pipeline status, warnings, and resource signals.',
    href: '/docs/dashboard-and-scans',
    image: '/docs/media/dashboard-overview.png',
  },
  {
    title: 'Sources',
    body: 'Confirm source type, readiness, root label, owner, and allowed scan actions.',
    href: '/docs/sources',
    image: '/docs/media/sources-list.png',
  },
  {
    title: 'Findings',
    body: 'Prioritize review work by risk, retention, owner, evidence count, and status.',
    href: '/docs/findings-and-review',
    image: '/docs/media/findings-list.png',
  },
]

const userTracks = [
  ['Reviewer', 'Start with Findings, then use Quick Start for the decision flow.'],
  ['Workspace admin', 'Start with Accounts and Workspaces, then Sources.'],
  ['Auditor', 'Start with Audit and Evaluation, then Safety Boundaries.'],
]

const quickStartSteps = [
  ['Sign in', 'Use Google or GitHub when the deployment requires authentication.'],
  ['Select Workspace', 'Confirm membership and visible permission boundaries before using privileged actions.'],
  ['Add source', 'Register a supported source and verify scan readiness.'],
  ['Start scan', 'Run a full scan from Dashboard or Sources against an explicit source.'],
  ['Review evidence', 'Open findings and inspect redacted evidence, owner, retention, and denied actions.'],
  ['Record decision', 'Submit only allowed decisions with required reasons and checklist acknowledgement.'],
  ['Verify audit', 'Confirm the review event and resulting status in the audit trail.'],
  ['Check evaluation', 'Review precision, recall, F1, reproducibility, throughput, and resource intensity.'],
]

const readinessChecks = [
  'You know which Workspace you are operating in.',
  'You can explain why the source is scan-ready.',
  'You can see allowed and denied actions before review.',
  'You understand that deletion is simulated in P0.',
]

type DocsScreenshotProps = {
  alt: string
  caption: string
  src: string
}

export function DocsScreenshot({ alt, caption, src }: DocsScreenshotProps) {
  return (
    <figure className="ds-screenshot">
      <a href={src} target="_blank" rel="noreferrer">
        <img alt={alt} src={src} />
      </a>
      <figcaption>
        <span>{caption}</span>
        <a href={src} target="_blank" rel="noreferrer">Open full size</a>
      </figcaption>
    </figure>
  )
}

export function HomeTopBar() {
  return (
    <header className="ds-home-nav">
      <a className="ds-home-brand" href="/docs">
        <span>DataSentinel</span>
        <strong>User Guide</strong>
      </a>
      <nav aria-label="Documentation home links">
        <a href="/docs/quick-start">Quick Start</a>
        <a href="/docs/safety-and-boundaries">Safety</a>
        <a href="/docs/faq">FAQ</a>
      </nav>
      <a className="ds-home-console" href="/dashboard">Open console</a>
    </header>
  )
}

export function GuideHero() {
  return (
    <section className="ds-hero">
      <div className="ds-hero-copy">
        <span className="ds-eyebrow">User guide</span>
        <h1>Run accountable data discovery without guessing the next step.</h1>
        <p>
          Start from a source, run a scan, review redacted evidence, record a human decision,
          and prove the workflow through audit and evaluation surfaces.
        </p>
        <div className="ds-actions">
          <a className="ds-button ds-button-primary" href="/docs/quick-start">Start quick guide</a>
          <a className="ds-button ds-button-secondary" href="/dashboard">Open console</a>
        </div>
        <div className="ds-proof-row" aria-label="Documentation boundaries">
          <span>No legal advice</span>
          <span>Deletion simulated</span>
          <span>Redacted evidence</span>
        </div>
      </div>
      <div className="ds-hero-panel" aria-label="DataSentinel workflow preview">
        <div className="ds-panel-top">
          <span>First review path</span>
          <strong>8 steps</strong>
        </div>
        <div className="ds-flow-list">
          {['Workspace', 'Source', 'Full scan', 'Finding', 'Decision', 'Audit', 'Evaluation'].map((item, index) => (
            <div className="ds-flow-item" key={item}>
              <span>{index + 1}</span>
              <strong>{item}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function FastTrack() {
  return (
    <section className="ds-section">
      <div className="ds-section-heading">
        <span className="ds-eyebrow">Fast track</span>
        <h2>Get oriented in under five minutes</h2>
      </div>
      <div className="ds-step-grid">
        {workflowSteps.map((step) => (
          <a className="ds-step-card" href={step.href} key={step.label}>
            <span>{step.label}</span>
            <strong>{step.title}</strong>
            <p>{step.body}</p>
          </a>
        ))}
      </div>
    </section>
  )
}

export function SurfaceCards() {
  return (
    <section className="ds-section">
      <div className="ds-section-heading">
        <span className="ds-eyebrow">Core surfaces</span>
        <h2>Jump to the page that matches your task</h2>
      </div>
      <div className="ds-card-grid">
        {surfaceCards.map((card) => (
          <a className={`ds-surface-card ds-accent-${card.accent}`} href={card.href} key={card.title}>
            <span>{card.eyebrow}</span>
            <strong>{card.title}</strong>
            <p>{card.body}</p>
          </a>
        ))}
      </div>
    </section>
  )
}

export function VisualTour() {
  return (
    <section className="ds-section">
      <div className="ds-section-heading">
        <span className="ds-eyebrow">Visual tour</span>
        <h2>Recognize the main product surfaces</h2>
      </div>
      <div className="ds-visual-grid">
        {visualTourCards.map((card) => (
          <a className="ds-visual-card" href={card.href} key={card.title}>
            <img alt={`${card.title} surface screenshot`} src={card.image} />
            <strong>{card.title}</strong>
            <p>{card.body}</p>
          </a>
        ))}
      </div>
    </section>
  )
}

export function UserTracks() {
  return (
    <section className="ds-section ds-track-section">
      <div>
        <span className="ds-eyebrow">Choose a path</span>
        <h2>Different users need different first pages</h2>
      </div>
      <div className="ds-track-list">
        {userTracks.map(([title, body]) => (
          <article className="ds-track" key={title}>
            <strong>{title}</strong>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

export function QuickStartHero() {
  return (
    <section className="ds-quick-hero">
      <div>
        <span className="ds-eyebrow">Quick start</span>
        <h1>Complete the first review loop with confidence.</h1>
        <p>
          Follow this path when you want to validate the product workflow end to end:
          sign in, select a Workspace, scan a source, review a finding, and verify audit and evaluation output.
        </p>
      </div>
      <a className="ds-button ds-button-primary" href="/dashboard">Open console</a>
    </section>
  )
}

export function QuickStartPath() {
  return (
    <section className="ds-section">
      <div className="ds-section-heading">
        <span className="ds-eyebrow">Step-by-step</span>
        <h2>The shortest safe path through DataSentinel</h2>
      </div>
      <ol className="ds-timeline">
        {quickStartSteps.map(([title, body], index) => (
          <li key={title}>
            <span>{String(index + 1).padStart(2, '0')}</span>
            <div>
              <strong>{title}</strong>
              <p>{body}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

export function ReadinessChecklist() {
  return (
    <section className="ds-check-panel">
      <div>
        <span className="ds-eyebrow">Before you decide</span>
        <h2>Four checks keep the workflow accountable</h2>
      </div>
      <ul>
        {readinessChecks.map((item) => (
          <li key={item}>
            <span aria-hidden="true">OK</span>
            <p>{item}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function SafetyBand() {
  return (
    <section className="ds-safety-band">
      <div>
        <span className="ds-eyebrow">Prototype boundary</span>
        <h2>Evidence supports humans. It does not replace them.</h2>
      </div>
      <p>
        DataSentinel does not provide legal advice, does not claim full GDPR compliance,
        and does not delete external files in P0.
      </p>
      <a href="/docs/safety-and-boundaries">Review safety boundaries</a>
    </section>
  )
}
