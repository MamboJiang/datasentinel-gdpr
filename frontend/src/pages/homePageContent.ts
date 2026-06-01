import {
  Activity,
  Database,
  FileSearch,
  Gauge,
  GitBranch,
  LockKeyhole,
  ShieldCheck,
  UserCheck,
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

export type GovernanceCardType =
  | 'toggles'
  | 'codeRule'
  | 'permissionBoundary'
  | 'ownerRouting'
  | 'reviewerGuidance'
  | 'auditRequirement'

export type GovernanceCardConfig = {
  title: string
  type: GovernanceCardType
  summary: string
}

type BoundarySection = {
  title: string
  description: string
  icon: LucideIcon
}

export const heroTitle = 'lawdit'

export const proofPoints: ProofPoint[] = [
  {
    title: 'Discover',
    description: 'Run bounded scans against controlled sources.',
    icon: Database,
    tone: 'red',
  },
  {
    title: 'Explain',
    description: 'Show redacted evidence, anchors, and confidence.',
    icon: FileSearch,
    tone: 'blue',
  },
  {
    title: 'Route',
    description: 'Send findings to owners or fallback reviewers.',
    icon: GitBranch,
    tone: 'green',
  },
  {
    title: 'Review',
    description: 'Require a human decision with a reason.',
    icon: UserCheck,
    tone: 'amber',
  },
  {
    title: 'Audit',
    description: 'Record scan, assignment, and review events.',
    icon: Activity,
    tone: 'ink',
  },
]

export const workflowSteps: WorkflowStep[] = [
  {
    title: 'Controlled source',
    description: 'The Workspace starts from a registered source, with the organizer sample repository available for local validation.',
  },
  {
    title: 'Full scan',
    description: 'A scan uses an explicit source ID and never starts from a not-ready source.',
  },
  {
    title: 'Inventory and extraction',
    description: 'File counts, fingerprints, extraction warnings, and redacted evidence candidates are summarized.',
  },
  {
    title: 'Evidence signals',
    description: 'Deterministic detectors produce masked snippets and safe location labels.',
  },
  {
    title: 'Context and risk',
    description: 'Policy-pack guidance helps prioritize review without producing legal advice or compliance claims.',
  },
  {
    title: 'Owner routing',
    description: 'Findings go to a direct Source owner, Master of Data fallback, or DPO escalation queue.',
  },
  {
    title: 'Review support',
    description: 'Reviewers see guidance, allowed actions, denied actions, and visible scopes before acting.',
  },
  {
    title: 'Human decision',
    description: 'Decisions require a reason and may retain, reassign, escalate, mark false positive, or flag deletion candidate.',
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

export const workflowNodeLabels = ['Source', 'Signals', 'Risk', 'Owner', 'Review', 'Audit']

export const workflowThreadPath = 'M50 -4 C74 8 74 22 50 31 C26 40 26 52 50 60 C74 68 74 82 50 90 C36 95 38 104 50 110'

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

export const workflowPhases = workflowNodeLabels.map((title, index) => {
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

export const workflowStepPhaseIndexes = workflowSteps.map((_, stepIndex) => {
  const phaseIndex = workflowPhaseStepIndexes.findIndex((stepIndexes) => stepIndexes.includes(stepIndex))

  return phaseIndex >= 0 ? phaseIndex : 0
})

export const scannerHits = ['Email address', 'Personal name', 'IBAN-like number']

export const scannerMissingControls = [
  'No owner',
  'No review decision',
  'No deletion justification',
  'No audit trail',
  'No delta proof',
]

export const governanceLoopSteps = [
  ['Explain evidence', 'Masked snippet + context + confidence'],
  ['Route owner', 'Source owner / Master of Data fallback / DPO escalation'],
  ['Require review', 'Retain / reassign / escalate / false positive / deletion candidate'],
  ['Record audit', 'Actor + reason + timestamp + outcome'],
  ['Keep alive', 'Delta scan checks only changed files'],
] as const

export const fileStatusCards = [
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

export const governanceCards: GovernanceCardConfig[] = [
  {
    title: 'Global Governance Settings',
    type: 'toggles',
    summary: 'Human justification, masked review, and simulated deletion only.',
  },
  {
    title: 'Active Escalation Rule',
    type: 'codeRule',
    summary: 'High-risk special-category data routes to Legal DPO.',
  },
  {
    title: 'Permission Boundary',
    type: 'permissionBoundary',
    summary: 'Allowed and denied scanner actions are visible before review.',
  },
  {
    title: 'Owner Routing Model',
    type: 'ownerRouting',
    summary: 'Risk cases route to accountable human owners.',
  },
  {
    title: 'Reviewer Guidance',
    type: 'reviewerGuidance',
    summary: 'Reviewers see redacted evidence, suggested next action, and required justification.',
  },
  {
    title: 'Audit Requirement',
    type: 'auditRequirement',
    summary: 'Every accepted review action records actor, evidence, decision, reason, and time.',
  },
]

export const governanceLayerLabels = ['Settings', 'Escalation', 'Boundary', 'Owner', 'Review', 'Audit']

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

export const safetyBoundaries: BoundarySection[] = [
  {
    title: 'Deletion stays gated',
    description: 'A deletion candidate is a human-review outcome in this environment; it never deletes external source files.',
    icon: ShieldCheck,
  },
  {
    title: 'Tenant access stays explicit',
    description: 'Sign-in and selected-source access do not grant Microsoft Graph, tenant inventory, hidden token exposure, or deletion rights.',
    icon: LockKeyhole,
  },
  {
    title: 'Evidence, not legal advice',
    description: 'lawdit shows governed workflow evidence without claiming full GDPR compliance or making legal determinations.',
    icon: Gauge,
  },
]
