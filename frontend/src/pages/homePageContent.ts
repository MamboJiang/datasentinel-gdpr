import {
  Activity,
  ClipboardCheck,
  Database,
  EyeOff,
  FileSearch,
  Gauge,
  GitBranch,
  History,
  LockKeyhole,
  Scale,
  Settings2,
  ShieldCheck,
  UserCheck,
  Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

type ProofTone = 'red' | 'blue' | 'green' | 'amber' | 'ink'

export type ProofPoint = {
  title: string
  description: string
  icon: LucideIcon
  tone: ProofTone
}

export type WorkflowStep = {
  title: string
  description: string
}

export type ContractSection = {
  title: string
  description: string
  icon: LucideIcon
}

export const proofPoints: ProofPoint[] = [
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

export const workflowSteps: WorkflowStep[] = [
  {
    title: 'Controlled source',
    description: 'The P0 demo starts from a referenced organizer sample source or mock-backed fixture.',
  },
  {
    title: 'Full scan',
    description: 'A scan uses an explicit source ID and never starts from a not-ready source.',
  },
  {
    title: 'Inventory and extraction',
    description: 'File counts, fingerprints, warnings, and redacted evidence candidates are summarized.',
  },
  {
    title: 'Evidence signals',
    description: 'Deterministic detectors produce masked snippets and safe location labels.',
  },
  {
    title: 'Context and risk',
    description: 'Policy-pack guidance helps prioritize review without producing legal conclusions.',
  },
  {
    title: 'Owner routing',
    description: 'Findings go to a direct owner, Master of Data fallback, or escalation queue.',
  },
  {
    title: 'Review support',
    description: 'Reviewers see guidance, allowed actions, denied actions, and visible scopes before acting.',
  },
  {
    title: 'Human decision',
    description: 'Decisions require a reason and may keep, reassign, escalate, mark false positive, or flag deletion candidate.',
  },
  {
    title: 'Audit trail',
    description: 'Accepted changes create attributable audit events with policy context.',
  },
  {
    title: 'Delta scan',
    description: 'Later scans can focus on changed files after a full-scan baseline.',
  },
  {
    title: 'Evaluation',
    description: 'Precision, recall, F1, reproducibility, throughput, and resource intensity stay visible.',
  },
]

export const contractSections: ContractSection[] = [
  {
    title: 'Problem to govern',
    description: 'Distributed file stores make manual review hard to scale, and simple detection is not enough without evidence, ownership, review, audit, and quality metrics.',
    icon: Scale,
  },
  {
    title: 'Redacted evidence',
    description: 'Reviewer-facing surfaces use masked snippets, safe metadata, and fallback locations instead of exposing raw source content.',
    icon: EyeOff,
  },
  {
    title: 'Accountable routing',
    description: 'Owner assignment, Master of Data fallback, and escalation paths prevent review-required findings from becoming silently unowned.',
    icon: Users,
  },
  {
    title: 'Human review',
    description: 'Guidance appears before action, permission boundaries stay visible, and every review decision needs human context.',
    icon: ClipboardCheck,
  },
  {
    title: 'Audit evidence',
    description: 'Scan, assignment, and review actions preserve actor, timestamp, reason, outcome, and policy context when available.',
    icon: History,
  },
  {
    title: 'Adaptable governance',
    description: 'Policy packs, organization models, permission boundaries, and change previews avoid hard-coding one legal snapshot into scanner logic.',
    icon: Settings2,
  },
]

export const evaluationMetrics = [
  { label: 'Precision', value: '0.941' },
  { label: 'Recall', value: '0.842' },
  { label: 'F1', value: '0.889' },
  { label: 'Model calls', value: '0' },
  { label: 'Estimated cost', value: '$0.00' },
  { label: 'Reproducibility', value: '1.0' },
]

export const sampleFamilies = [
  'Expense_Report',
  'IT_Access_Request',
  'Incident_Report',
  'Supplier_Onboarding',
  'Training_Evaluation',
]

export const consoleSurfaces = [
  'Dashboard',
  'Sources',
  'Findings',
  'Finding detail and evidence card',
  'File review editor',
  'Review panel',
  'Audit view',
  'Evaluation',
  'Governance settings',
  'Permission boundary',
]

export const safetyBoundaries: ContractSection[] = [
  {
    title: 'Deletion is simulated',
    description: 'delete_candidate is a review status in P0 and does not execute source-file deletion.',
    icon: ShieldCheck,
  },
  {
    title: 'No production tenant integration',
    description: 'The prototype does not connect to production Microsoft Graph, OAuth, tenant systems, parser, OCR, queue, database, AI, or deletion services.',
    icon: LockKeyhole,
  },
  {
    title: 'No legal advice claim',
    description: 'DataSentinel shows governed workflow evidence without claiming full GDPR compliance or legal determinations.',
    icon: Gauge,
  },
]
