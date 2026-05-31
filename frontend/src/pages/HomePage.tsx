import { ArrowRight, ExternalLink } from 'lucide-react'
import { useEffect, useRef, useState, type MouseEvent, type PointerEvent } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import {
  consoleSurfaces,
  contractSections,
  evaluationMetrics,
  proofPoints,
  safetyBoundaries,
  sampleFamilies,
  workflowSteps,
} from './homePageContent'
import './HomePage.css'
import './HomePage.sections.css'
import './HomePage.responsive.css'

gsap.registerPlugin(ScrollTrigger)

const heroTitle = 'DataSentinel'
const workflowNodeLabels = ['Source', 'Signals', 'Risk', 'Owner', 'Review', 'Audit']
const workflowStepNodeMap = [0, 0, 0, 1, 2, 3, 4, 4, 5, 5, 5]
const workflowPhaseStepIndexes = [
  [0, 1],
  [2, 3],
  [4],
  [5],
  [6, 7],
  [8, 9, 10],
]
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function HomePage() {
  const rootRef = useRef<HTMLDivElement>(null)
  const [activeWorkflowNodeIndex, setActiveWorkflowNodeIndex] = useState<number | null>(null)
  const [visibleHeroTitleLength, setVisibleHeroTitleLength] = useState(() => (prefersReducedMotion() ? heroTitle.length : 0))
  const [heroTitleOpacity, setHeroTitleOpacity] = useState(() => (prefersReducedMotion() ? 1 : 0))
  const [isHeroTitleTyping, setIsHeroTitleTyping] = useState(() => !prefersReducedMotion())
  const [isWorkflowDetailOpen, setIsWorkflowDetailOpen] = useState(false)
  const visibleHeroTitle = heroTitle.slice(0, visibleHeroTitleLength)
  const visibleWorkflowNodeIndex = activeWorkflowNodeIndex ?? 0
  const visibleWorkflowStepIndexes = isWorkflowDetailOpen
    ? workflowPhaseStepIndexes[visibleWorkflowNodeIndex]
    : workflowSteps.map((_, index) => index)

  function handleSectionLink(event: MouseEvent<HTMLAnchorElement>, sectionId: string) {
    const section = document.getElementById(sectionId)

    if (!section) {
      return
    }

    event.preventDefault()
    window.history.replaceState(null, '', `#${sectionId}`)
    section.scrollIntoView({ behavior: 'auto', block: 'start' })
    window.setTimeout(() => section.focus({ preventScroll: true }), 0)
  }

  function handleHeroCardPointerMove(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    const x = (event.clientX - bounds.left) / bounds.width - 0.5
    const y = (event.clientY - bounds.top) / bounds.height - 0.5
    const maxTilt = 5

    event.currentTarget.style.setProperty('--tilt-x', `${(-y * maxTilt).toFixed(2)}deg`)
    event.currentTarget.style.setProperty('--tilt-y', `${(x * maxTilt).toFixed(2)}deg`)
  }

  function handleHeroCardPointerLeave(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.style.setProperty('--tilt-x', '0deg')
    event.currentTarget.style.setProperty('--tilt-y', '0deg')
  }

  function selectPreviousWorkflowPhase() {
    setActiveWorkflowNodeIndex((current) => Math.max((current ?? 0) - 1, 0))
  }

  function selectNextWorkflowPhase() {
    setActiveWorkflowNodeIndex((current) => Math.min((current ?? 0) + 1, workflowNodeLabels.length - 1))
  }

  function openWorkflowPhase(index: number) {
    setActiveWorkflowNodeIndex(index)
    setIsWorkflowDetailOpen(true)
  }

  function resetWorkflowPhase() {
    setActiveWorkflowNodeIndex(null)
    setIsWorkflowDetailOpen(false)
  }

  useEffect(() => {
    const root = rootRef.current
    if (!root) {
      return
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const ctx = gsap.context(() => {
      if (prefersReducedMotion) {
        return
      }

      gsap.from('.landing-nav-shell', {
        autoAlpha: 0,
        duration: 0.7,
        ease: 'power3.out',
        y: -16,
      })

      gsap.from('.landing-hero-copy > :not(.landing-hero-title)', {
        autoAlpha: 0,
        duration: 0.85,
        ease: 'power3.out',
        stagger: 0.08,
        y: 28,
      })

      gsap.to('.landing-parallax-slow', {
        scrollTrigger: {
          end: 'bottom top',
          scrub: 1.1,
          start: 'top top',
          trigger: '.landing-hero',
        },
        y: -90,
      })

      gsap.to('.landing-parallax-medium', {
        rotation: -2,
        scrollTrigger: {
          end: 'bottom top',
          scrub: 0.9,
          start: 'top top',
          trigger: '.landing-hero',
        },
        x: 28,
        y: -145,
      })

      gsap.to('.landing-parallax-fast', {
        rotation: 3,
        scrollTrigger: {
          end: 'bottom top',
          scrub: 0.75,
          start: 'top top',
          trigger: '.landing-hero',
        },
        x: -34,
        y: -205,
      })

      gsap.to('.landing-workflow-depth-grid', {
        scrollTrigger: {
          end: 'bottom top',
          scrub: 1.15,
          start: 'top bottom',
          trigger: '.landing-workflow',
        },
        y: -96,
      })

      gsap.utils.toArray<HTMLElement>('.landing-reveal').forEach((element) => {
        gsap.from(element, {
          autoAlpha: 0,
          duration: 0.8,
          ease: 'power2.out',
          scrollTrigger: {
            start: 'top 82%',
            toggleActions: 'play none none reverse',
            trigger: element,
          },
          y: 44,
        })
      })

    }, root)

    const refreshId = window.setTimeout(() => ScrollTrigger.refresh(), 120)

    return () => {
      window.clearTimeout(refreshId)
      ctx.revert()
    }
  }, [])

  useEffect(() => {
    if (prefersReducedMotion()) {
      return
    }

    const startTime = window.performance.now()
    const duration = 1250

    const intervalId = window.setInterval(() => {
      const timestamp = window.performance.now()
      const progress = Math.min((timestamp - startTime) / duration, 1)
      const easedProgress = 1 - Math.pow(1 - progress, 3)
      const nextLength = Math.min(heroTitle.length, Math.floor(easedProgress * heroTitle.length))

      setVisibleHeroTitleLength(nextLength)
      setHeroTitleOpacity(Math.min(1, progress * 1.15))

      if (progress >= 1) {
        window.clearInterval(intervalId)
        setVisibleHeroTitleLength(heroTitle.length)
        setHeroTitleOpacity(1)
        setIsHeroTitleTyping(false)
      }
    }, 32)

    return () => window.clearInterval(intervalId)
  }, [])

  return (
    <div className="landing-page" ref={rootRef}>
      <div className="landing-announcement">
        <span>DataSentinel prelaunch uses signed-in access, redacted evidence, and human review.</span>
        <a href="#safety" onClick={(event) => handleSectionLink(event, 'safety')}>
          Review boundaries <ArrowRight aria-hidden="true" size={14} />
        </a>
      </div>

      <header className="landing-nav-shell">
        <Link className="landing-brand" to="/">
          <span className="landing-mark" aria-hidden="true">
            <i /><i /><i /><i /><i /><i /><i /><i /><i />
          </span>
          <span>DataSentinel</span>
        </Link>
        <nav className="landing-nav" aria-label="Homepage navigation">
          <a href="#problem" onClick={(event) => handleSectionLink(event, 'problem')}>Problem</a>
          <a href="#workflow" onClick={(event) => handleSectionLink(event, 'workflow')}>Workflow</a>
          <a href="#sample" onClick={(event) => handleSectionLink(event, 'sample')}>Sources</a>
          <a href="#safety" onClick={(event) => handleSectionLink(event, 'safety')}>Safety</a>
        </nav>
        <Link className="landing-nav-cta" to="/dashboard">Open dashboard</Link>
      </header>

      <main>
        <section className="landing-hero" id="overview" tabIndex={-1}>
          <div className="landing-hero-scene" aria-hidden="true">
            <div className="landing-scene-grid" />
            <div
              className="landing-file-card landing-parallax-slow"
              onPointerLeave={handleHeroCardPointerLeave}
              onPointerMove={handleHeroCardPointerMove}
            >
              <div className="landing-card-face">
                <div className="landing-file-card-header">
                  <span>Configured source file</span>
                  <strong>Needs review</strong>
                </div>
                <p>Identifier: [REDACTED]</p>
                <p>Contact: [REDACTED_EMAIL]</p>
                <small>Evidence anchors stay masked</small>
              </div>
            </div>
            <div
              className="landing-route-card landing-parallax-medium"
              onPointerLeave={handleHeroCardPointerLeave}
              onPointerMove={handleHeroCardPointerMove}
            >
              <div className="landing-card-face">
                <span>Owner route</span>
                <strong>Accountable owner</strong>
                <div className="landing-route-graph">
                  <i /> <b /> <i />
                </div>
                <small>Assigned for human review</small>
              </div>
            </div>
            <div
              className="landing-audit-card landing-parallax-fast"
              onPointerLeave={handleHeroCardPointerLeave}
              onPointerMove={handleHeroCardPointerMove}
            >
              <div className="landing-card-face">
                <span>Audit trail</span>
                <p>scan started</p>
                <p>finding assigned</p>
                <p>review recorded</p>
              </div>
            </div>
          </div>

          <div className="landing-hero-copy">
            <h1
              aria-label={heroTitle}
              className="landing-hero-title"
              style={{ opacity: heroTitleOpacity }}
            >
              <span aria-hidden="true" className="landing-hero-title-text">
                {visibleHeroTitle}
                {isHeroTitleTyping ? <span className="landing-hero-title-caret" /> : null}
              </span>
              <span aria-hidden="true" className="landing-hero-title-measure">{heroTitle}</span>
            </h1>
            <p>
              Evidence-backed GDPR-relevant data discovery that routes findings to accountable owners, requires human review,
              and records audit-ready workflow evidence.
            </p>
            <div className="landing-hero-actions">
              <Link className="landing-primary landing-hero-primary" to="/dashboard">
                <span className="landing-primary-content">
                  Open dashboard <ArrowRight aria-hidden="true" size={17} />
                </span>
              </Link>
              <a className="landing-secondary" href="#workflow" onClick={(event) => handleSectionLink(event, 'workflow')}>Review workflow</a>
            </div>
          </div>

          <div className="landing-action-flow" aria-hidden="true">
            <svg viewBox="0 0 1180 210" preserveAspectRatio="none">
              <defs>
                <linearGradient id="landing-flow-gradient" x1="0%" x2="100%" y1="0%" y2="0%">
                  <stop offset="0%" stopColor="#0b57d0" stopOpacity="0" />
                  <stop offset="26%" stopColor="#0b57d0" stopOpacity=".28" />
                  <stop offset="52%" stopColor="#147a42" stopOpacity=".2" />
                  <stop offset="78%" stopColor="#62666c" stopOpacity=".18" />
                  <stop offset="100%" stopColor="#0b57d0" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path className="landing-flow-path" d="M18 118 C170 92 304 112 438 108 C520 106 548 88 604 88 C674 88 706 112 780 112 C914 112 1018 88 1162 104" />
              <path className="landing-flow-trace" d="M18 118 C170 92 304 112 438 108 C520 106 548 88 604 88 C674 88 706 112 780 112 C914 112 1018 88 1162 104" />
            </svg>
          </div>

        </section>

        <section className="landing-feature-rail" aria-label="DataSentinel capabilities">
          {proofPoints.map(({ title, description, icon: Icon, tone }) => (
            <article className={`landing-proof landing-proof-${tone}`} key={title}>
              <Icon aria-hidden="true" size={20} strokeWidth={1.9} />
              <strong>{title}</strong>
              <p>{description}</p>
            </article>
          ))}
        </section>

        <section className="landing-section landing-problem" id="problem" tabIndex={-1}>
          <div className="landing-section-copy landing-reveal">
            <h2>Detection is only the opening move.</h2>
            <p>
              Personal data can be scattered across distributed file stores. Manual auditing does not scale, and a plain
              PII hit list cannot explain evidence, ownership, review decisions, auditability, or measurable quality.
            </p>
          </div>
          <div className="landing-contract-grid">
            {contractSections.map(({ title, description, icon: Icon }) => (
              <article className="landing-contract-card landing-reveal" key={title}>
                <Icon aria-hidden="true" size={24} />
                <strong>{title}</strong>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section landing-workflow" id="workflow" tabIndex={-1}>
          <div className="landing-workflow-depth-grid" aria-hidden="true" />
          <div className="landing-section-copy landing-reveal">
            <h2>From source files to accountable review.</h2>
            <p>
              DataSentinel is not a generic PII scanner or an automatic deletion tool. Detection starts a governed loop that
              keeps redaction, ownership, review support, permission boundaries, audit, delta scans, and evaluation visible.
            </p>
          </div>
          <div className="landing-workflow-layout">
            <div className="landing-workflow-visual landing-reveal" aria-hidden="true">
              <span className="landing-workflow-visual-hint">Click a phase for details</span>
              {workflowNodeLabels.map((label, index) => (
                <div className="landing-workflow-flow-item" key={label}>
                  <button
                    className={`landing-workflow-node${isWorkflowDetailOpen && visibleWorkflowNodeIndex === index ? ' landing-workflow-node-active' : ''}`}
                    type="button"
                    onClick={() => openWorkflowPhase(index)}
                    onFocus={() => setActiveWorkflowNodeIndex(index)}
                  >
                    {label}
                  </button>
                  {index < workflowNodeLabels.length - 1 ? (
                    <div className={`landing-workflow-line${isWorkflowDetailOpen && (visibleWorkflowNodeIndex === index || visibleWorkflowNodeIndex === index + 1) ? ' landing-workflow-line-active' : ''}`} />
                  ) : null}
                </div>
              ))}
            </div>
            <div className={`landing-workflow-steps-shell landing-reveal${isWorkflowDetailOpen ? ' landing-workflow-steps-shell-detail' : ' landing-workflow-steps-shell-overview'}`}>
              <div className="landing-workflow-steps" key={isWorkflowDetailOpen ? visibleWorkflowNodeIndex : 'overview'}>
                <div className="landing-workflow-panel-top">
                  <span className="landing-workflow-phase-label">
                    {isWorkflowDetailOpen ? workflowNodeLabels[visibleWorkflowNodeIndex] : 'All workflow steps'}
                  </span>
                  {isWorkflowDetailOpen ? (
                    <button className="landing-workflow-back" type="button" onClick={resetWorkflowPhase}>
                      Back
                    </button>
                  ) : null}
                </div>
                {isWorkflowDetailOpen ? (
                  <button
                    aria-label="Show previous workflow phase"
                    className="landing-workflow-switch landing-workflow-switch-top"
                    disabled={visibleWorkflowNodeIndex === 0}
                    type="button"
                    onClick={selectPreviousWorkflowPhase}
                  >
                    <ArrowRight aria-hidden="true" size={16} />
                  </button>
                ) : null}
                {visibleWorkflowStepIndexes.map((stepIndex) => {
                  const step = workflowSteps[stepIndex]
                  return (
                  <article
                    className="landing-workflow-step landing-workflow-step-visible"
                    key={step.title}
                    onMouseEnter={() => {
                      if (isWorkflowDetailOpen) {
                        setActiveWorkflowNodeIndex(workflowStepNodeMap[stepIndex] ?? null)
                      }
                    }}
                  >
                    <span>{String(stepIndex + 1).padStart(2, '0')}</span>
                    <div>
                      <strong>{step.title}</strong>
                      {isWorkflowDetailOpen ? <p>{step.description}</p> : null}
                    </div>
                  </article>
                  )
                })}
                {isWorkflowDetailOpen ? (
                  <button
                    aria-label="Show next workflow phase"
                    className="landing-workflow-switch landing-workflow-switch-bottom"
                    disabled={visibleWorkflowNodeIndex === workflowNodeLabels.length - 1}
                    type="button"
                    onClick={selectNextWorkflowPhase}
                  >
                    <ArrowRight aria-hidden="true" size={16} />
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section landing-sample" id="sample" tabIndex={-1}>
          <div className="landing-section-copy landing-reveal">
            <h2>Connect a source before findings appear.</h2>
            <p>
              Prelaunch deployments should show configured sources and real empty states. The public organizer repository
              remains available as a reference dataset for local validation without vendoring the files.
            </p>
          </div>
          <div className="landing-sample-layout">
            <article className="landing-sample-card landing-reveal">
              <span>Optional validation reference</span>
              <strong>Organizer GDPR Data Samples</strong>
              <a href="https://github.com/a-klumpp/GDPR-data-samples" rel="noreferrer" target="_blank">
                Open reference dataset <ExternalLink aria-hidden="true" size={14} />
              </a>
            </article>
            <div className="landing-sample-families landing-reveal" aria-label="Sample families">
              {sampleFamilies.map((family) => <span key={family}>{family}</span>)}
            </div>
          </div>
        </section>

        <section className="landing-section landing-governance" id="governance" tabIndex={-1}>
          <div className="landing-governance-copy landing-reveal">
            <h2>Governance stays explicit.</h2>
            <p>
              Policy packs, organization models, permission boundaries, reviewer guidance, and escalation choices stay visible
              instead of being hidden inside scanner logic.
            </p>
          </div>
          <div className="landing-console-preview">
            <div className="landing-console-list landing-reveal" aria-label="Internal console surfaces">
              {consoleSurfaces.map((surface) => <span key={surface}>{surface}</span>)}
            </div>
            <div className="landing-console-copy landing-reveal">
              <strong>Enter the internal workspace.</strong>
              <p>
                The console starts at /dashboard after sign-in and keeps homepage navigation separate from the internal shell.
              </p>
              <Link className="landing-primary" to="/dashboard">
                Open dashboard <ArrowRight aria-hidden="true" size={17} />
              </Link>
            </div>
          </div>
        </section>

        <section className="landing-section landing-evaluation" id="evaluation" tabIndex={-1}>
          <div className="landing-evaluation-board landing-reveal">
            <div>
              <h2>Measured, not guessed.</h2>
              <p>
                Evaluation keeps accuracy, reproducibility, throughput, and resource intensity in view after a scan has produced
                measurable results.
              </p>
            </div>
            <dl>
              {evaluationMetrics.map((metric) => (
                <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}</dd></div>
              ))}
            </dl>
          </div>
        </section>

        <section className="landing-section landing-safety" id="safety" tabIndex={-1}>
          <div className="landing-section-copy landing-reveal">
            <h2>Safe prototype boundaries stay visible.</h2>
            <p>
              The public homepage and internal console avoid raw sensitive content, legal advice, full-compliance claims,
              automatic deletion, and production integration promises.
            </p>
          </div>
          <div className="landing-safety-grid">
            {safetyBoundaries.map(({ title, description, icon: Icon }) => (
              <article className="landing-safety-card landing-reveal" key={title}>
                <Icon aria-hidden="true" size={24} />
                <strong>{title}</strong>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-final">
          <h2>Enter the privacy operations workspace.</h2>
          <Link className="landing-primary" to="/dashboard">
            Open dashboard <ArrowRight aria-hidden="true" size={17} />
          </Link>
        </section>
      </main>
    </div>
  )
}
