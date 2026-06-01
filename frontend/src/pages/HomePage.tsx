import { ArrowRight, Check, ExternalLink, X } from 'lucide-react'
import { useEffect, useRef, useState, type CSSProperties, type MouseEvent, type PointerEvent, type WheelEvent } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import {
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
const workflowThreadPath = 'M50 -4 C74 8 74 22 50 31 C26 40 26 52 50 60 C74 68 74 82 50 90 C36 95 38 104 50 110'
const workflowPhaseStepIndexes = [
  [0, 1],
  [2, 3],
  [4],
  [5],
  [6, 7],
  [8, 9, 10],
]
const workflowPhaseSummaries = [
  {
    summary: 'Controlled sources and scan readiness are established before findings exist.',
    objective: 'Start from an explicit source and a reliable full-scan baseline.',
    output: 'Configured source evidence and scan readiness.',
  },
  {
    summary: 'Inventory, extraction, and detector signals become safe evidence candidates.',
    objective: 'Turn raw files into masked, explainable review signals.',
    output: 'File inventory, warnings, and redacted evidence snippets.',
  },
  {
    summary: 'Policy-pack context turns findings into review priorities without legal conclusions.',
    objective: 'Separate signal severity from human legal decisions.',
    output: 'Risk context for accountable review.',
  },
  {
    summary: 'Findings route to accountable humans instead of remaining silently unowned.',
    objective: 'Assign direct owners or escalate when ownership is unknown.',
    output: 'Owner queue with fallback routing.',
  },
  {
    summary: 'Reviewers see allowed actions, denied actions, and required reasons before acting.',
    objective: 'Require a human decision before cleanup action.',
    output: 'Decision support with visible permission boundaries.',
  },
  {
    summary: 'Accepted changes become attributable, measurable, and audit-ready.',
    objective: 'Preserve traceability and keep later scans focused.',
    output: 'Audit events, delta baseline, and evaluation visibility.',
  },
]
const fallbackWorkflowPhaseSummary = workflowPhaseSummaries[0] ?? {
  summary: 'Workflow activity is grouped into accountable review phases.',
  objective: 'Keep each phase visible before a decision is made.',
  output: 'Review-ready workflow context.',
}
const workflowPhases = workflowNodeLabels.map((title, index) => {
  const stepIndexes = workflowPhaseStepIndexes[index] ?? []
  const firstStep = stepIndexes[0] ?? 0
  const lastStep = stepIndexes[stepIndexes.length - 1] ?? firstStep
  const detail = workflowPhaseSummaries[index] ?? fallbackWorkflowPhaseSummary

  return {
    id: title.toLowerCase(),
    title,
    range: `${String(firstStep + 1).padStart(2, '0')}-${String(lastStep + 1).padStart(2, '0')}`,
    stepIndexes,
    ...detail,
  }
})
const workflowStepPhaseIndexes = workflowSteps.map((_, stepIndex) => {
  const phaseIndex = workflowPhaseStepIndexes.findIndex((stepIndexes) => stepIndexes.includes(stepIndex))

  return phaseIndex >= 0 ? phaseIndex : 0
})

const scannerHits = ['Email address', 'Personal name', 'IBAN-like number']
const scannerMissingControls = [
  'No owner',
  'No review decision',
  'No deletion justification',
  'No audit trail',
  'No delta proof',
]
const governanceLoopSteps = [
  ['Explain evidence', 'Masked snippet + context + confidence'],
  ['Route owner', 'File owner / site owner / Master of Data / DPO'],
  ['Require review', 'Delete / retain / redact / escalate with justification'],
  ['Record audit', 'Actor + reason + timestamp + outcome'],
  ['Keep alive', 'Delta scan checks only changed files'],
] as const
const fileStatusCards = [
  {
    id: 'detected',
    eyebrow: '01 / Detection',
    title: 'Detected',
    description: 'GDPR-relevant content found. Masked evidence and entity types are extracted before any review starts.',
    meta: ['Evidence: Masked', 'Risk: Scored', 'Source: Controlled'],
    tone: 'blue-gray',
  },
  {
    id: 'ownership',
    eyebrow: '02 / Ownership',
    title: 'Owner assigned',
    description:
      'The case is routed to a file owner, site owner, Master of Data, or DPO fallback when ownership is unclear.',
    meta: ['Route: Accountable', 'Fallback: Master of Data', 'Escalation: Available'],
    tone: 'neutral',
  },
  {
    id: 'review',
    eyebrow: '03 / Review',
    title: 'Review required',
    description: 'A human reviewer sees masked snippets, context, confidence, and guidance before making a decision.',
    meta: ['Evidence: Redacted', 'Reviewer: Required', 'Guidance: Visible'],
    tone: 'amber-gray',
  },
  {
    id: 'decision',
    eyebrow: '04 / Decision',
    title: 'Decision recorded',
    description: 'Delete, retain, redact, or escalate actions must include a human justification before being closed.',
    meta: ['Delete: Approval required', 'Retain: Exception reason', 'Blind delete: Disabled'],
    tone: 'charcoal',
  },
  {
    id: 'audit',
    eyebrow: '05 / Audit',
    title: 'Audit-ready',
    description: 'Actor, timestamp, evidence, decision, reason, and outcome are preserved as an audit trail.',
    meta: ['Actor: Tracked', 'Reason: Stored', 'Outcome: Traceable'],
    tone: 'green-gray',
  },
  {
    id: 'delta',
    eyebrow: '06 / Delta scan',
    title: 'Delta monitored',
    description: 'Future scans process only changed files, keeping the compliance baseline alive without full rescans.',
    meta: ['Changed files: Scanned', 'Baseline: Updated', 'Governance: Continuous'],
    tone: 'violet-gray',
  },
]

type GovernanceCardType =
  | 'toggles'
  | 'codeRule'
  | 'permissionBoundary'
  | 'ownerRouting'
  | 'reviewerGuidance'
  | 'auditRequirement'

type GovernanceCardConfig = {
  title: string
  type: GovernanceCardType
  summary: string
}

const governanceCards: GovernanceCardConfig[] = [
  {
    title: 'Global Governance Settings',
    type: 'toggles',
    summary: 'Human justification, masked review, and no automatic deletion.',
  },
  {
    title: 'Active Escalation Rule',
    type: 'codeRule',
    summary: 'High-risk special-category data routes to Legal DPO.',
  },
  {
    title: 'Permission Boundary',
    type: 'permissionBoundary',
    summary: 'Scanner actions are allowed and denied explicitly.',
  },
  {
    title: 'Owner Routing Model',
    type: 'ownerRouting',
    summary: 'Risk cases route to accountable human owners.',
  },
  {
    title: 'Reviewer Guidance',
    type: 'reviewerGuidance',
    summary: 'Reviewers see evidence, suggested action, and required justification.',
  },
  {
    title: 'Audit Requirement',
    type: 'auditRequirement',
    summary: 'Every decision records actor, evidence, decision, reason, and time.',
  },
]

const governanceLayerLabels = ['Settings', 'Escalation', 'Boundary', 'Owner', 'Review', 'Audit']
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

type TrueFocusProps = {
  animationDuration?: number
  blurAmount?: number
  borderColor?: string
  className?: string
  glowColor?: string
  manualMode?: boolean
  pauseBetweenAnimations?: number
  sentence: string
}

function TrueFocus({
  animationDuration = 0.45,
  blurAmount = 2.4,
  borderColor = 'rgba(11, 87, 208, .52)',
  className = '',
  glowColor = 'rgba(11, 87, 208, .14)',
  manualMode = false,
  pauseBetweenAnimations = 1.1,
  sentence,
}: TrueFocusProps) {
  const words = sentence.split(' ')
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    if (manualMode || words.length <= 1 || prefersReducedMotion()) return undefined

    const interval = window.setInterval(() => {
      setActiveIndex((index) => (index + 1) % words.length)
    }, (animationDuration + pauseBetweenAnimations) * 1000)

    return () => window.clearInterval(interval)
  }, [animationDuration, manualMode, pauseBetweenAnimations, words.length])

  return (
    <span
      aria-label={sentence}
      className={`landing-true-focus ${className}`.trim()}
      role="text"
      style={{
        '--true-focus-blur': `${blurAmount}px`,
        '--true-focus-border': borderColor,
        '--true-focus-duration': `${animationDuration}s`,
        '--true-focus-glow': glowColor,
      } as CSSProperties}
    >
      {words.map((word, index) => (
        <span
          aria-hidden="true"
          className={`landing-true-focus-word${index === activeIndex ? ' landing-true-focus-word-active' : ''}`}
          key={`${word}-${index}`}
        >
          <span>{word}</span>
        </span>
      ))}
    </span>
  )
}

export function HomePage() {
  const rootRef = useRef<HTMLDivElement>(null)
  const dotGridCanvasRef = useRef<HTMLCanvasElement>(null)
  const fileStatusDragStartXRef = useRef(0)
  const fileStatusDragStartIndexRef = useRef(0)
  const fileStatusDidDragRef = useRef(false)
  const fileStatusWheelTimerRef = useRef<number | null>(null)
  const [activeWorkflowNodeIndex, setActiveWorkflowNodeIndex] = useState<number | null>(null)
  const [visibleHeroTitleLength, setVisibleHeroTitleLength] = useState(() => (prefersReducedMotion() ? heroTitle.length : 0))
  const [heroTitleOpacity, setHeroTitleOpacity] = useState(() => (prefersReducedMotion() ? 1 : 0))
  const [isHeroTitleTyping, setIsHeroTitleTyping] = useState(() => !prefersReducedMotion())
  const [isWorkflowDetailOpen, setIsWorkflowDetailOpen] = useState(false)
  const [activeGovernanceIndex, setActiveGovernanceIndex] = useState(0)
  const [isGovernanceFolderOpen, setIsGovernanceFolderOpen] = useState(false)
  const [activeFileStatusIndex, setActiveFileStatusIndex] = useState(0)
  const [fileStatusDragOffset, setFileStatusDragOffset] = useState(0)
  const [isFileStatusDragging, setIsFileStatusDragging] = useState(false)
  const [isFileStatusHovered, setIsFileStatusHovered] = useState(false)
  const visibleHeroTitle = heroTitle.slice(0, visibleHeroTitleLength)
  const visibleWorkflowNodeIndex = activeWorkflowNodeIndex ?? 0
  const visibleWorkflowPhase = workflowPhases[visibleWorkflowNodeIndex]
  const activeGovernanceCard = governanceCards[activeGovernanceIndex] ?? governanceCards[0]
  const activeFileStatus = fileStatusCards[activeFileStatusIndex] ?? fileStatusCards[0]

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

  function openWorkflowStep(stepIndex: number) {
    openWorkflowPhase(workflowStepPhaseIndexes[stepIndex] ?? 0)
  }

  function resetWorkflowPhase() {
    setActiveWorkflowNodeIndex(null)
    setIsWorkflowDetailOpen(false)
  }

  function selectGovernanceCard(index: number) {
    setIsGovernanceFolderOpen(true)
    setActiveGovernanceIndex(index)
  }

  function selectFileStatus(index: number) {
    const total = fileStatusCards.length
    const nextIndex = ((index % total) + total) % total

    setActiveFileStatusIndex(nextIndex)
    setFileStatusDragOffset(0)
  }

  function handleFileStatusPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (event.pointerType === 'mouse' && event.button !== 0) return

    fileStatusDragStartXRef.current = event.clientX
    fileStatusDragStartIndexRef.current = activeFileStatusIndex
    fileStatusDidDragRef.current = false
    setIsFileStatusDragging(true)
    setFileStatusDragOffset(0)
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function handleFileStatusPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!isFileStatusDragging) return

    const nextOffset = event.clientX - fileStatusDragStartXRef.current
    if (Math.abs(nextOffset) > 8) {
      fileStatusDidDragRef.current = true
    }

    setFileStatusDragOffset(nextOffset)
  }

  function handleFileStatusPointerEnd(event: PointerEvent<HTMLDivElement>) {
    if (!isFileStatusDragging) return

    const cardStep = 180
    const indexShift = Math.round(-fileStatusDragOffset / cardStep)
    const nextIndex = fileStatusDragStartIndexRef.current + indexShift

    setIsFileStatusDragging(false)
    selectFileStatus(nextIndex)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  function handleFileStatusWheel(event: WheelEvent<HTMLDivElement>) {
    const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY

    if (Math.abs(delta) < 24 || fileStatusWheelTimerRef.current !== null) return

    event.preventDefault()
    selectFileStatus(activeFileStatusIndex + (delta > 0 ? 1 : -1))
    fileStatusWheelTimerRef.current = window.setTimeout(() => {
      fileStatusWheelTimerRef.current = null
    }, 420)
  }

  function getFileStatusPosition(index: number) {
    const total = fileStatusCards.length
    let position = index - activeFileStatusIndex

    if (position > total / 2) position -= total
    if (position < -total / 2) position += total

    return position + fileStatusDragOffset / 180
  }

  function renderGovernanceCardContent(card: GovernanceCardConfig, isActive: boolean) {
    if (!isActive) {
      return <p className="landing-governance-card-summary">{card.summary}</p>
    }

    switch (card.type) {
      case 'toggles':
        return (
          <div className="landing-governance-toggle-list">
            {[
              ['Require human justification', true],
              ['Mask PII in review mode', true],
              ['Auto-delete without review', false],
            ].map(([label, isOn]) => (
              <div className="landing-governance-toggle-row" key={String(label)}>
                <span>{label}</span>
                <i className={`landing-governance-toggle${isOn ? ' landing-governance-toggle-on' : ''}`} aria-hidden="true" />
              </div>
            ))}
          </div>
        )
      case 'codeRule':
        return (
          <div className="landing-governance-code">
            <div>IF Risk_Score &gt;= <mark>High</mark></div>
            <div>AND Category == <mark>Special_PII</mark></div>
            <div>THEN Route_To = <mark>Legal_DPO</mark></div>
          </div>
        )
      case 'permissionBoundary':
        return (
          <div className="landing-governance-boundary">
            <div>
              <strong>Scanner can</strong>
              {['Detect sensitive data', 'Recommend review action'].map((item) => (
                <span key={item}><Check aria-hidden="true" size={15} />{item}</span>
              ))}
            </div>
            <div>
              <strong>Scanner cannot</strong>
              {['Delete without approval', 'Reveal masked PII'].map((item) => (
                <span className="landing-governance-denied" key={item}><X aria-hidden="true" size={15} />{item}</span>
              ))}
            </div>
          </div>
        )
      case 'ownerRouting':
        return (
          <div className="landing-governance-routing">
            {[
              ['OneDrive Owner', 'Direct Owner'],
              ['SharePoint Site', 'Site Owner'],
              ['Shared Drive', 'Master of Data'],
              ['High Risk + Unknown Owner', 'DPO'],
            ].map(([source, owner]) => (
              <div key={source}>
                <span>{source}</span>
                <b>to</b>
                <strong>{owner}</strong>
              </div>
            ))}
          </div>
        )
      case 'reviewerGuidance':
        return (
          <div className="landing-governance-guidance">
            <span>Detected</span>
            <strong>Health Data + Personal Identifier</strong>
            <span>Suggested Action</span>
            <b>Mask before external sharing</b>
            <em>Justification before decision</em>
          </div>
        )
      case 'auditRequirement':
        return (
          <div className="landing-governance-audit">
            <span>Audit-ready</span>
            {['Actor', 'Evidence', 'Decision', 'Justification', 'Timestamp'].map((item) => (
              <div key={item}><Check aria-hidden="true" size={15} />{item}</div>
            ))}
          </div>
        )
      default:
        return null
    }
  }

  useEffect(() => {
    const canvas = dotGridCanvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context) {
      return
    }

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const dotSize = 1.35
    const gap = 24
    const proximity = 170
    const hoverStrength = 8
    const shockRadius = 230
    const shockStrength = 12
    const resistance = 0.88
    const returnSpeed = 0.055
    const baseColor = { r: 148, g: 163, b: 184 }
    const activeColor = { r: 11, g: 87, b: 208 }
    const pointer = { active: false, x: -9999, y: -9999 }
    type Dot = {
      originX: number
      originY: number
      xOffset: number
      yOffset: number
      velocityX: number
      velocityY: number
    }
    let dots: Dot[] = []
    let frameId = 0
    let width = 0
    let height = 0

    const setCanvasSize = () => {
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = Math.ceil(width * pixelRatio)
      canvas.height = Math.ceil(height * pixelRatio)
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

      const columns = Math.ceil(width / gap) + 2
      const rows = Math.ceil(height / gap) + 2
      dots = []

      for (let row = 0; row < rows; row += 1) {
        for (let column = 0; column < columns; column += 1) {
          dots.push({
            originX: column * gap - gap / 2,
            originY: row * gap - gap / 2,
            velocityX: 0,
            velocityY: 0,
            xOffset: 0,
            yOffset: 0,
          })
        }
      }
    }

    const handlePointerMove = (event: WindowEventMap['pointermove']) => {
      if (motionQuery.matches) {
        return
      }

      const rect = canvas.getBoundingClientRect()
      pointer.active = true
      pointer.x = event.clientX - rect.left
      pointer.y = event.clientY - rect.top
    }

    const handlePointerLeave = () => {
      pointer.active = false
      pointer.x = -9999
      pointer.y = -9999
    }

    const handlePointerDown = (event: WindowEventMap['pointerdown']) => {
      if (motionQuery.matches) {
        return
      }

      dots.forEach((dot) => {
        const deltaX = dot.originX - event.clientX
        const deltaY = dot.originY - event.clientY
        const distance = Math.hypot(deltaX, deltaY)

        if (distance > shockRadius || distance === 0) {
          return
        }

        const falloff = 1 - distance / shockRadius
        dot.velocityX += (deltaX / distance) * shockStrength * falloff
        dot.velocityY += (deltaY / distance) * shockStrength * falloff
      })
    }

    const renderDotGrid = () => {
      context.clearRect(0, 0, width, height)

      dots.forEach((dot) => {
        dot.velocityX *= resistance
        dot.velocityY *= resistance
        dot.xOffset += dot.velocityX
        dot.yOffset += dot.velocityY
        dot.xOffset += (0 - dot.xOffset) * returnSpeed
        dot.yOffset += (0 - dot.yOffset) * returnSpeed

        const deltaX = pointer.active ? dot.originX - pointer.x : 0
        const deltaY = pointer.active ? dot.originY - pointer.y : 0
        const distance = pointer.active ? Math.hypot(deltaX, deltaY) : Infinity
        const influence = Math.max(0, 1 - distance / proximity)
        const easedInfluence = influence * influence * (3 - 2 * influence)
        const hoverX = distance > 0 && distance < proximity ? (deltaX / distance) * easedInfluence * hoverStrength : 0
        const hoverY = distance > 0 && distance < proximity ? (deltaY / distance) * easedInfluence * hoverStrength : 0
        const x = dot.originX + dot.xOffset + hoverX
        const y = dot.originY + dot.yOffset + hoverY
        const radius = dotSize + easedInfluence * 2.2
        const opacity = 0.18 + easedInfluence * 0.56
        const red = Math.round(baseColor.r + (activeColor.r - baseColor.r) * easedInfluence)
        const green = Math.round(baseColor.g + (activeColor.g - baseColor.g) * easedInfluence)
        const blue = Math.round(baseColor.b + (activeColor.b - baseColor.b) * easedInfluence)

        context.beginPath()
        context.fillStyle = `rgba(${red}, ${green}, ${blue}, ${opacity})`
        context.arc(x, y, radius, 0, Math.PI * 2)
        context.fill()
      })

      frameId = window.requestAnimationFrame(renderDotGrid)
    }

    setCanvasSize()
    frameId = window.requestAnimationFrame(renderDotGrid)
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerdown', handlePointerDown)
    window.addEventListener('resize', setCanvasSize)
    window.addEventListener('blur', handlePointerLeave)
    document.addEventListener('pointerleave', handlePointerLeave)

    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerdown', handlePointerDown)
      window.removeEventListener('resize', setCanvasSize)
      window.removeEventListener('blur', handlePointerLeave)
      document.removeEventListener('pointerleave', handlePointerLeave)
    }
  }, [])

  useEffect(() => {
    if (prefersReducedMotion() || isFileStatusDragging || isFileStatusHovered) {
      return undefined
    }

    const interval = window.setInterval(() => {
      setActiveFileStatusIndex((index) => (index + 1) % fileStatusCards.length)
      setFileStatusDragOffset(0)
    }, 3200)

    return () => window.clearInterval(interval)
  }, [isFileStatusDragging, isFileStatusHovered])

  useEffect(() => {
    return () => {
      if (fileStatusWheelTimerRef.current !== null) {
        window.clearTimeout(fileStatusWheelTimerRef.current)
      }
    }
  }, [])

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
    const duration = 1700

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
      <canvas className="landing-dot-grid-background" ref={dotGridCanvasRef} aria-hidden="true" />
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
            <h2 className="landing-problem-title">
              <TrueFocus
                animationDuration={0.45}
                blurAmount={2.4}
                borderColor="rgba(11, 87, 208, .52)"
                glowColor="rgba(11, 87, 208, .14)"
                pauseBetweenAnimations={1.1}
                sentence="From detection to accountable action."
              />
            </h2>
            <p>
              A scanner only finds sensitive data. DataSentinel explains why it matters, who owns the decision, what
              action is required, and how the outcome is proven.
            </p>
          </div>
          <div className="landing-conversion-layout" aria-label="Scanner to governance comparison">
            <article className="landing-scanner-card landing-reveal">
              <div className="landing-problem-card-topline">
                <span>Detection only</span>
                <span>Incomplete</span>
              </div>
              <h3>Plain scanner</h3>
              <p>Stops at detection</p>
              <div className="landing-scanner-output">
                <strong>PII hits found:</strong>
                <ul>
                  {scannerHits.map((hit) => (
                    <li key={hit}>{hit}</li>
                  ))}
                </ul>
              </div>
              <div className="landing-scanner-missing">
                <strong>Missing:</strong>
                <ul>
                  {scannerMissingControls.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </article>

            <div className="landing-conversion-connector landing-reveal" aria-hidden="true">
              <span>Detection</span>
              <i><ArrowRight size={20} /></i>
              <span>Governance</span>
            </div>

            <article className="landing-governance-loop-card landing-reveal">
              <div className="landing-problem-card-topline">
                <span>Control plane</span>
                <span>Review case</span>
              </div>
              <h3>DataSentinel control tower</h3>
              <p>Turns findings into accountable decisions</p>
              <div className="landing-governance-loop">
                {governanceLoopSteps.map(([title, description], index) => (
                  <div className="landing-governance-loop-row" key={title}>
                    <span>{String(index + 1).padStart(2, '0')}</span>
                    <div>
                      <strong>{title}</strong>
                      <p>{description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </div>
          <p className="landing-accountability-callout landing-reveal">
            We do not delete blindly. We make deletion decisions accountable.
          </p>
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
              <div
                className="beam-wrapper"
                style={{
                  height: '100%',
                  left: 0,
                  maskImage: 'linear-gradient(to bottom, transparent 0%, transparent 18%, black 24%, black 84%, transparent 100%)',
                  overflow: 'hidden',
                  pointerEvents: 'none',
                  position: 'absolute',
                  top: 0,
                  WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, transparent 18%, black 24%, black 84%, transparent 100%)',
                  width: '100%',
                  zIndex: 1,
                }}
              >
                <style>{`
                  :root {
                    --beam-duration: 7s;
                    --beam-delay: 0s;
                    --beam-ease: cubic-bezier(0.4, 0, 0.2, 1);
                  }
                  @keyframes track-pulse {
                    0%, 100% { opacity: 0.04; }
                    50% { opacity: 0.16; }
                  }
                  @keyframes rail-glow-breathe {
                    0%, 100% {
                      opacity: 0.08;
                      transform: scale(1);
                    }
                    50% {
                      opacity: 0.2;
                      transform: scale(1.015);
                    }
                  }
                  .rail-breathe {
                    animation: rail-glow-breathe 6.5s ease-in-out infinite;
                    filter: blur(18px);
                    transform-box: fill-box;
                    transform-origin: center;
                  }
                  .rail-aura {
                    animation: track-pulse 4s ease-in-out infinite;
                    filter: blur(12px);
                  }
                  .rail-solid {
                    animation: track-pulse 4s ease-in-out infinite;
                  }
                  @keyframes beam-flow {
                    0% {
                      opacity: 0;
                      stroke-dashoffset: 2120;
                    }
                    8% {
                      opacity: 0;
                      stroke-dashoffset: 2120;
                    }
                    15% {
                      opacity: 1;
                      stroke-dashoffset: 2000;
                    }
                    65% {
                      opacity: 1;
                      stroke-dashoffset: 0;
                    }
                    75% {
                      opacity: 0;
                      stroke-dashoffset: -120;
                    }
                    100% {
                      opacity: 0;
                      stroke-dashoffset: -120;
                    }
                  }
                  .comet-flow {
                    animation: beam-flow var(--beam-duration) var(--beam-ease) var(--beam-delay) infinite;
                    opacity: 0;
                    stroke-dashoffset: 2120;
                  }
                  .comet-flow path {
                    stroke-dashoffset: inherit;
                  }
                  .comet-tail {
                    stroke-dasharray: 140 1860;
                    opacity: .76;
                    filter: blur(8px);
                  }
                  .comet-core {
                    stroke-dasharray: 140 1860;
                    opacity: .92;
                    filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.9));
                    transform: translate(0, 0);
                  }
                `}</style>

                <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none" style={{ minHeight: '800px', overflow: 'hidden' }}>
                  <g>
                    <path
                      d={workflowThreadPath}
                      fill="none"
                      stroke="#6D5DF6"
                      strokeWidth="22"
                      strokeLinecap="round"
                      className="rail-breathe"
                    />
                    <path
                      d={workflowThreadPath}
                      fill="none"
                      stroke="#4F46E5"
                      strokeWidth="12"
                      strokeLinecap="round"
                      className="rail-aura"
                    />
                    <path
                      d={workflowThreadPath}
                      fill="none"
                      stroke="#3B82F6"
                      strokeWidth="2"
                      strokeLinecap="round"
                      className="rail-solid"
                    />
                    <g className="comet-flow">
                      <path
                        d={workflowThreadPath}
                        fill="none"
                        stroke="#60A5FA"
                        strokeWidth="8"
                        strokeLinecap="round"
                        pathLength={2000}
                        className="comet-tail"
                      />
                      <path
                        d={workflowThreadPath}
                        fill="none"
                        stroke="#ffffff"
                        strokeWidth="2"
                        strokeLinecap="round"
                        pathLength={2000}
                        className="comet-core"
                      />
                    </g>
                  </g>
                </svg>
              </div>
              <div className="landing-workflow-phase-stack">
                {workflowNodeLabels.map((label, index) => (
                  <div className="landing-workflow-flow-item" key={label}>
                    <button
                      className={`landing-workflow-node${isWorkflowDetailOpen && visibleWorkflowNodeIndex === index ? ' landing-workflow-node-active' : ''}`}
                      type="button"
                      onClick={() => openWorkflowPhase(index)}
                      onFocus={() => setActiveWorkflowNodeIndex(index)}
                    >
                      <span>{label}</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <div className={`landing-workflow-steps-shell landing-reveal${isWorkflowDetailOpen ? ' landing-workflow-steps-shell-detail' : ' landing-workflow-steps-shell-overview'}`}>
              <div className="landing-workflow-steps" key={isWorkflowDetailOpen ? visibleWorkflowNodeIndex : 'overview'}>
                {!isWorkflowDetailOpen ? (
                  <>
                    <div className="landing-workflow-panel-top">
                      <span className="landing-workflow-phase-label">All workflow steps</span>
                    </div>
                    <div className="landing-workflow-overview-grid">
                      {workflowSteps.map((step, stepIndex) => {
                        const phaseIndex = workflowStepPhaseIndexes[stepIndex] ?? 0

                        return (
                          <button
                            className="landing-workflow-step landing-workflow-overview-step"
                            key={step.title}
                            onClick={() => openWorkflowStep(stepIndex)}
                            style={{ '--workflow-step-delay': `${stepIndex * 35}ms` } as CSSProperties}
                            type="button"
                          >
                            <span>{String(stepIndex + 1).padStart(2, '0')}</span>
                            <div>
                              <strong>{step.title}</strong>
                              <small>{workflowNodeLabels[phaseIndex]}</small>
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="landing-workflow-detail-header">
                      <div>
                        <span className="landing-workflow-phase-label">{visibleWorkflowPhase.title}</span>
                        <strong>{visibleWorkflowPhase.range}</strong>
                      </div>
                      <button className="landing-workflow-back" type="button" onClick={resetWorkflowPhase}>
                        All steps
                      </button>
                    </div>
                    <article className="landing-workflow-detail-summary">
                      <span>Phase objective</span>
                      <h3>{visibleWorkflowPhase.summary}</h3>
                      <dl>
                        <div>
                          <dt>Goal</dt>
                          <dd>{visibleWorkflowPhase.objective}</dd>
                        </div>
                        <div>
                          <dt>Output</dt>
                          <dd>{visibleWorkflowPhase.output}</dd>
                        </div>
                      </dl>
                    </article>
                    <div className="landing-workflow-detail-step-grid">
                      {visibleWorkflowPhase.stepIndexes.map((stepIndex, index) => {
                        const step = workflowSteps[stepIndex]

                        return (
                          <article
                            className="landing-workflow-detail-step"
                            key={step.title}
                            style={{ '--workflow-step-delay': `${index * 70}ms` } as CSSProperties}
                          >
                            <span>{String(stepIndex + 1).padStart(2, '0')}</span>
                            <div>
                              <strong>{step.title}</strong>
                              <p>{step.description}</p>
                              <small>{visibleWorkflowPhase.title} phase</small>
                            </div>
                          </article>
                        )
                      })}
                    </div>
                    <div className="landing-workflow-detail-footer">
                      <button
                        className="landing-workflow-phase-control"
                        disabled={visibleWorkflowNodeIndex === 0}
                        type="button"
                        onClick={selectPreviousWorkflowPhase}
                      >
                        Previous phase
                      </button>
                      <div className="landing-workflow-mini-timeline" aria-label="Workflow phase progress">
                        {workflowPhases.map((phase, index) => (
                          <button
                            aria-label={`Show ${phase.title} phase`}
                            className={index === visibleWorkflowNodeIndex ? 'landing-workflow-mini-dot-active' : ''}
                            key={phase.id}
                            type="button"
                            onClick={() => openWorkflowPhase(index)}
                          />
                        ))}
                      </div>
                      <button
                        className="landing-workflow-phase-control"
                        disabled={visibleWorkflowNodeIndex === workflowPhases.length - 1}
                        type="button"
                        onClick={selectNextWorkflowPhase}
                      >
                        Next phase
                      </button>
                    </div>
                  </>
                )}
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
            <aside className={`landing-policy-selector landing-reveal${isGovernanceFolderOpen ? ' landing-policy-selector-open' : ''}`} aria-label="Policy pack files">
              <div className="landing-policy-selector-top">
                <div>
                  <span>Policy pack</span>
                  <strong>Governance files</strong>
                </div>
                <b className="landing-policy-selector-count">
                  {String(activeGovernanceIndex + 1).padStart(2, '0')} / {String(governanceCards.length).padStart(2, '0')}
                </b>
              </div>
              <button
                aria-label="Preview policy pack folder"
                className="landing-policy-mini-folder"
                type="button"
                onClick={() => setIsGovernanceFolderOpen((current) => !current)}
                onMouseEnter={() => setIsGovernanceFolderOpen(true)}
                onMouseLeave={() => setIsGovernanceFolderOpen(false)}
              >
                <span className="landing-policy-mini-folder-back">
                  {governanceLayerLabels.slice(0, 3).map((label, index) => (
                    <i className={`landing-policy-mini-paper landing-policy-mini-paper-${index + 1}`} key={label}>
                      {label}
                    </i>
                  ))}
                  <span className="landing-policy-mini-folder-front">
                    <b>Policy pack</b>
                    <small>{governanceLayerLabels[activeGovernanceIndex]}</small>
                  </span>
                </span>
              </button>
              <div className="landing-policy-selector-files" aria-label="Governance files">
                {governanceLayerLabels.map((label, index) => (
                  <button
                    aria-pressed={index === activeGovernanceIndex}
                    className={index === activeGovernanceIndex ? 'landing-policy-selector-file-active' : ''}
                    key={label}
                    type="button"
                    onClick={() => selectGovernanceCard(index)}
                  >
                    <span>{label}</span>
                    <small>{governanceCards[index].title}</small>
                  </button>
                ))}
              </div>
              <div className="landing-policy-selector-dots" aria-hidden="true">
                {governanceCards.map((card, index) => (
                  <span className={index === activeGovernanceIndex ? 'landing-policy-selector-dot-active' : ''} key={card.title} />
                ))}
              </div>
            </aside>
            <div className="landing-governance-main landing-reveal" aria-live="polite">
              <div className="landing-governance-card-stack">
                {governanceCards.slice(1).map((card, index) => (
                  <span
                    className={`landing-governance-stack-shadow landing-governance-stack-shadow-${index + 1}`}
                    key={`${card.title}-shadow`}
                  />
                ))}
                <article className="landing-governance-active-card" key={activeGovernanceCard.title}>
                  <div className="landing-governance-card-heading">
                    <span>Active policy layer</span>
                    <strong>{activeGovernanceCard.title}</strong>
                  </div>
                  <div className="landing-governance-active-content">
                    {renderGovernanceCardContent(activeGovernanceCard, true)}
                  </div>
                </article>
              </div>
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
          <div className="landing-evaluation-copy landing-reveal">
            <h2>Every file has a visible status.</h2>
            <p>
              Each finding moves through a governed lifecycle: detected, assigned, reviewed, decided, audited, and monitored by
              delta scans.
            </p>
          </div>
          <div
            aria-label="File status lifecycle gallery"
            className={`landing-file-status-gallery landing-reveal${isFileStatusDragging ? ' landing-file-status-gallery-dragging' : ''}`}
            role="region"
            onMouseEnter={() => setIsFileStatusHovered(true)}
            onMouseLeave={() => setIsFileStatusHovered(false)}
            onPointerCancel={handleFileStatusPointerEnd}
            onPointerDown={handleFileStatusPointerDown}
            onPointerMove={handleFileStatusPointerMove}
            onPointerUp={handleFileStatusPointerEnd}
            onWheel={handleFileStatusWheel}
          >
            <div className="landing-file-status-stage">
              {fileStatusCards.map((status, index) => {
                const position = getFileStatusPosition(index)
                const absPosition = Math.min(Math.abs(position), 3)
                const isActive = index === activeFileStatusIndex && Math.abs(fileStatusDragOffset) < 36

                return (
                  <article
                    aria-hidden={Math.abs(position) > 2.75}
                    className={`landing-file-status-card landing-file-status-card-${status.tone}${isActive ? ' landing-file-status-card-active' : ''}`}
                    key={status.id}
                    role="button"
                    style={{
                      '--status-arc-y': `${absPosition * absPosition * 18}px`,
                      '--status-opacity': `${Math.max(0.34, 1 - absPosition * 0.22)}`,
                      '--status-position': position,
                      '--status-rotate': `${position * -5.4}deg`,
                      '--status-scale': `${Math.max(0.72, 1 - absPosition * 0.105)}`,
                      zIndex: 20 - Math.round(absPosition * 4),
                    } as CSSProperties}
                    tabIndex={Math.abs(position) <= 2.75 ? 0 : -1}
                    onClick={() => {
                      if (!fileStatusDidDragRef.current) {
                        selectFileStatus(index)
                      }
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        selectFileStatus(index)
                      }
                    }}
                  >
                    <div className="landing-file-status-card-top">
                      <span>{status.eyebrow}</span>
                      <b>{String(index + 1).padStart(2, '0')}</b>
                    </div>
                    <strong>{status.title}</strong>
                    <p>{status.description}</p>
                    <div className="landing-file-status-meta">
                      {status.meta.map((item) => {
                        const [label, value] = item.split(': ')

                        return (
                          <span key={item}>
                            <small>{label}</small>
                            <em>{value}</em>
                          </span>
                        )
                      })}
                    </div>
                  </article>
                )
              })}
            </div>
            <div className="landing-file-status-indicator">
              <strong>{activeFileStatus.title}</strong>
              <span>
                {String(activeFileStatusIndex + 1).padStart(2, '0')} / {String(fileStatusCards.length).padStart(2, '0')}
              </span>
              <div aria-label="Select file status" className="landing-file-status-dots">
                {fileStatusCards.map((status, index) => (
                  <button
                    aria-label={`Show ${status.title} status`}
                    className={index === activeFileStatusIndex ? 'landing-file-status-dot-active' : ''}
                    key={`${status.id}-dot`}
                    type="button"
                    onClick={() => selectFileStatus(index)}
                  />
                ))}
              </div>
            </div>
            <p className="landing-file-status-hint">Drag or scroll to inspect the governed file lifecycle.</p>
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
