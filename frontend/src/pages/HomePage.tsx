import { ArrowRight, ExternalLink } from 'lucide-react'
import { useEffect, useRef, type MouseEvent } from 'react'
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

export function HomePage() {
  const rootRef = useRef<HTMLDivElement>(null)

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

      gsap.from('.landing-hero-copy > *', {
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

      gsap.from('.landing-workflow-step', {
        autoAlpha: 0,
        duration: 0.75,
        ease: 'power2.out',
        scrollTrigger: {
          start: 'top 72%',
          toggleActions: 'play none none reverse',
          trigger: '.landing-workflow-steps',
        },
        stagger: 0.12,
        x: -24,
      })
    }, root)

    const refreshId = window.setTimeout(() => ScrollTrigger.refresh(), 120)

    return () => {
      window.clearTimeout(refreshId)
      ctx.revert()
    }
  }, [])

  return (
    <div className="landing-page" ref={rootRef}>
      <div className="landing-announcement">
        <span>DataSentinel P0 is mock-backed, redacted, and human-reviewed.</span>
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
          <a href="#sample" onClick={(event) => handleSectionLink(event, 'sample')}>Sample</a>
          <a href="#safety" onClick={(event) => handleSectionLink(event, 'safety')}>Safety</a>
        </nav>
        <Link className="landing-nav-cta" to="/dashboard">Open dashboard</Link>
      </header>

      <main>
        <section className="landing-hero" id="overview" tabIndex={-1}>
          <div className="landing-hero-scene" aria-hidden="true">
            <div className="landing-scene-grid" />
            <div className="landing-file-card landing-parallax-slow">
              <div>
                <span>supplier_onboarding_2021.pdf</span>
                <strong>High risk</strong>
              </div>
              <p>IBAN: DE** **** **** ****</p>
              <p>Contact: [REDACTED_EMAIL]</p>
              <small>Page 1 · 2 evidence anchors</small>
            </div>
            <div className="landing-route-card landing-parallax-medium">
              <span>Owner route</span>
              <strong>Finance Master of Data</strong>
              <div>
                <i /> <b /> <i />
              </div>
              <small>Assigned for human review</small>
            </div>
            <div className="landing-audit-card landing-parallax-fast">
              <span>Audit trail</span>
              <p>scan_started</p>
              <p>finding_assigned</p>
              <p>review_recorded</p>
            </div>
          </div>

          <div className="landing-hero-copy">
            <h1>DataSentinel</h1>
            <p>
              Evidence-backed GDPR-relevant data discovery that routes findings to accountable owners, requires human review,
              and records audit-ready workflow evidence.
            </p>
            <div className="landing-hero-actions">
              <Link className="landing-primary" to="/dashboard">
                Open dashboard <ArrowRight aria-hidden="true" size={17} />
              </Link>
              <a className="landing-secondary" href="#workflow" onClick={(event) => handleSectionLink(event, 'workflow')}>Review workflow</a>
            </div>
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
          <div className="landing-section-copy landing-reveal">
            <h2>From source files to accountable review.</h2>
            <p>
              DataSentinel is not a generic PII scanner or an automatic deletion tool. Detection starts a governed loop that
              keeps redaction, ownership, review support, permission boundaries, audit, delta scans, and evaluation visible.
            </p>
          </div>
          <div className="landing-workflow-layout">
            <div className="landing-workflow-visual landing-reveal" aria-hidden="true">
              <div className="landing-workflow-node">Source</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Signals</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Risk</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Owner</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Review</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Audit</div>
            </div>
            <div className="landing-workflow-steps">
              {workflowSteps.map((step, index) => (
                <article className="landing-workflow-step" key={step.title}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div>
                    <strong>{step.title}</strong>
                    <p>{step.description}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section landing-sample" id="sample" tabIndex={-1}>
          <div className="landing-section-copy landing-reveal">
            <h2>Controlled sample source, not live enterprise data.</h2>
            <p>
              The default demo references the organizer repository a-klumpp/GDPR-data-samples and uses controlled sample
              or mock-backed behavior. The sample PDFs are referenced, not vendored into this project.
            </p>
          </div>
          <div className="landing-sample-layout">
            <article className="landing-sample-card landing-reveal">
              <span>Reference source</span>
              <strong>Organizer GDPR Data Samples</strong>
              <a href="https://github.com/a-klumpp/GDPR-data-samples" rel="noreferrer" target="_blank">
                Open repository reference <ExternalLink aria-hidden="true" size={14} />
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
              <strong>Inspect the internal workspace simulation.</strong>
              <p>
                The console starts at /dashboard and keeps homepage navigation separate from the internal shell.
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
                Evaluation keeps accuracy, reproducibility, throughput, and resource intensity in view. Mock-backed values are
                prototype evidence, not production certification.
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
