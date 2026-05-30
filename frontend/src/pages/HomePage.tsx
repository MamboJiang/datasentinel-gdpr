import { Activity, ArrowRight, Database, FileSearch, GitBranch, Scale, ShieldCheck, UserCheck } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './HomePage.css'
import './HomePage.sections.css'
import './HomePage.responsive.css'

gsap.registerPlugin(ScrollTrigger)

const proofPoints = [
  {
    title: 'Discover',
    description: 'Find GDPR-relevant files in controlled sources.',
    icon: Database,
    tone: 'red',
  },
  {
    title: 'Explain',
    description: 'Show masked evidence and detector confidence.',
    icon: FileSearch,
    tone: 'blue',
  },
  {
    title: 'Route',
    description: 'Assign findings to accountable owners.',
    icon: GitBranch,
    tone: 'green',
  },
  {
    title: 'Review',
    description: 'Require a human decision and reason.',
    icon: UserCheck,
    tone: 'amber',
  },
  {
    title: 'Audit',
    description: 'Record workflow events for traceability.',
    icon: Activity,
    tone: 'ink',
  },
]

const workflowSteps = [
  'Controlled sample source is scanned without exposing raw file bodies.',
  'Evidence is reduced to masked snippets, page labels, and risk context.',
  'Findings move to the right owner, queue, or escalation path.',
  'Every review decision captures the actor, reason, and resulting state.',
]

export function HomePage() {
  const rootRef = useRef<HTMLDivElement>(null)

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
        <span>DataSentinel P0 prototype is ready for GDPR evidence review.</span>
        <a href="#workflow">See the workflow <ArrowRight aria-hidden="true" size={14} /></a>
      </div>

      <header className="landing-nav-shell">
        <Link className="landing-brand" to="/">
          <span className="landing-mark" aria-hidden="true">
            <i /><i /><i /><i /><i /><i /><i /><i /><i />
          </span>
          <span>DataSentinel</span>
        </Link>
        <nav className="landing-nav" aria-label="Homepage navigation">
          <a href="#workflow">Workflow</a>
          <a href="#governance">Governance</a>
          <a href="#evaluation">Evaluation</a>
        </nav>
        <Link className="landing-nav-cta" to="/dashboard">Open dashboard</Link>
      </header>

      <main>
        <section className="landing-hero" id="overview">
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
              <strong>Anna Schneider</strong>
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
            <p>GDPR data discovery with evidence, owner routing, human review, and audit trails.</p>
            <div className="landing-hero-actions">
              <Link className="landing-primary" to="/dashboard">
                Open dashboard <ArrowRight aria-hidden="true" size={17} />
              </Link>
              <a className="landing-secondary" href="#workflow">Review workflow</a>
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

        <section className="landing-section landing-workflow" id="workflow">
          <div className="landing-section-copy landing-reveal">
            <h2>From source files to accountable review.</h2>
            <p>
              DataSentinel is not an automatic deletion tool. It turns controlled scans into evidence-backed findings,
              routes them to accountable people, and records the human decision path.
            </p>
          </div>
          <div className="landing-workflow-layout">
            <div className="landing-workflow-visual landing-reveal" aria-hidden="true">
              <div className="landing-workflow-node">Scan</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Evidence</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Owner</div>
              <div className="landing-workflow-line" />
              <div className="landing-workflow-node">Review</div>
            </div>
            <div className="landing-workflow-steps">
              {workflowSteps.map((step, index) => (
                <article className="landing-workflow-step" key={step}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <p>{step}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section landing-governance" id="governance">
          <div className="landing-governance-copy landing-reveal">
            <h2>Governance stays explicit.</h2>
            <p>
              Policy packs, permission boundaries, reviewer guidance, and escalation choices stay visible instead of
              being hidden inside scanner logic.
            </p>
          </div>
          <div className="landing-governance-grid">
            <article className="landing-governance-item landing-reveal">
              <ShieldCheck aria-hidden="true" size={24} />
              <strong>Masked by default</strong>
              <p>Evidence snippets are redacted before they reach reviewer-facing surfaces.</p>
            </article>
            <article className="landing-governance-item landing-reveal">
              <Scale aria-hidden="true" size={24} />
              <strong>No legal shortcuts</strong>
              <p>The workflow supports human decisions without claiming automated compliance.</p>
            </article>
            <article className="landing-governance-item landing-reveal">
              <UserCheck aria-hidden="true" size={24} />
              <strong>Accountable ownership</strong>
              <p>Every assigned finding has an owner, a reason path, and an audit event trail.</p>
            </article>
          </div>
        </section>

        <section className="landing-section landing-evaluation" id="evaluation">
          <div className="landing-evaluation-board landing-reveal">
            <div>
              <h2>Measured, not guessed.</h2>
              <p>Evaluation keeps precision, recall, reproducibility, throughput, and resource intensity in view.</p>
            </div>
            <dl>
              <div><dt>Precision</dt><dd>0.91</dd></div>
              <div><dt>Recall</dt><dd>0.86</dd></div>
              <div><dt>F1</dt><dd>0.88</dd></div>
              <div><dt>Cost</dt><dd>$0.00</dd></div>
            </dl>
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
