import type { LucideIcon } from 'lucide-react'
import {
  BookOpen,
  ClipboardList,
  FileQuestion,
  History,
  Home,
  LifeBuoy,
  LogOut,
  ShieldCheck,
  SmilePlus,
  UserRound,
} from 'lucide-react'

export const accountSimulation = {
  actorId: 'user_anna',
  email: 'anna.schneider@example.com',
  name: 'Anna Schneider',
}

export const workspaceSimulation = {
  description: 'Privacy operations workspace',
  id: 'datasentinel-gdpr',
  name: 'DataSentinel GDPR',
  plan: 'Demo',
}

export type UtilityRoute = {
  description: string
  icon: LucideIcon
  label: string
  path: string
  title: string
}

export const utilityRoutes: UtilityRoute[] = [
  {
    description: 'Review the simulated actor, workspace, roles, and permission boundary.',
    icon: UserRound,
    label: 'Account settings',
    path: '/account',
    title: 'Account Settings',
  },
  {
    description: 'Capture local prototype feedback without transmitting it outside the browser.',
    icon: SmilePlus,
    label: 'Feedback',
    path: '/feedback',
    title: 'Feedback',
  },
  {
    description: 'Return to the public DataSentinel homepage.',
    icon: Home,
    label: 'Home Page',
    path: '/',
    title: 'Home Page',
  },
  {
    description: 'Read the P0 prototype change log.',
    icon: History,
    label: 'Changelog',
    path: '/changelog',
    title: 'Changelog',
  },
  {
    description: 'Open task-oriented help for the console workflow.',
    icon: LifeBuoy,
    label: 'Help',
    path: '/help',
    title: 'Help',
  },
  {
    description: 'Inspect the local project documentation map.',
    icon: BookOpen,
    label: 'Docs',
    path: '/docs',
    title: 'Docs',
  },
  {
    description: 'View the mock-backed platform status surface.',
    icon: ShieldCheck,
    label: 'Platform status',
    path: '/status',
    title: 'Platform Status',
  },
  {
    description: 'Inspect the prototype plan boundary. Billing is not implemented.',
    icon: ClipboardList,
    label: 'Prototype plan',
    path: '/plan',
    title: 'Prototype Plan',
  },
  {
    description: 'Review the simulated sign-out boundary.',
    icon: LogOut,
    label: 'Log Out',
    path: '/session',
    title: 'Session Boundary',
  },
]

export const utilityPageTitles = Object.fromEntries(utilityRoutes.map((route) => [route.path, route.title]))

export const helpTopics = [
  {
    title: 'Start from a controlled source',
    description: 'Use Dashboard or Sources to start the allowed full scan for the mock-ready organizer sample source.',
    path: '/sources',
  },
  {
    title: 'Review evidence safely',
    description: 'Open a finding detail page to inspect redacted evidence, risk explanation, owner assignment, and review support.',
    path: '/findings',
  },
  {
    title: 'Check audit and evaluation',
    description: 'Use audit and evaluation pages to inspect traceability, deterministic metrics, and zero paid-service cost.',
    path: '/audit',
  },
]

export const documentationMap = [
  {
    title: 'Frontend console contract',
    description: 'Functional contract for internal routes, shell behavior, permissions, and safe rendering.',
    reference: 'docs/FRONTEND_CONSOLE_CONTRACT.md',
  },
  {
    title: 'Homepage contract',
    description: 'Public homepage content and safety boundaries.',
    reference: 'docs/WEBSITE_HOMEPAGE_CONTRACT.md',
  },
  {
    title: 'API contract',
    description: 'Envelope shape, P0 endpoints, problem details, and compatibility rules.',
    reference: 'docs/API_CONTRACT.md',
  },
  {
    title: 'Governance configuration',
    description: 'Policy packs, organization model, review support, and permission boundaries.',
    reference: 'docs/GOVERNANCE_CONFIG.md',
  },
]

export const changelogItems = [
  {
    title: 'Account menu utility routes',
    description: 'Account settings, feedback, docs, help, status, plan, and session-boundary pages now open from the account menu.',
  },
  {
    title: 'Homepage contract coverage',
    description: 'The public homepage explains workflow, sample source, evaluation, governance, and safe prototype boundaries.',
  },
  {
    title: 'Delta scan representation',
    description: 'The console can represent changed-file-only work after a completed full-scan baseline.',
  },
]

export const sessionBoundaries = [
  'No production authentication session is created or destroyed in P0.',
  'The visible actor remains a seeded demo actor for review and permission-boundary simulation.',
  'Log out records no external event and does not revoke any real tenant, OAuth, or Microsoft Graph access.',
]

export const planBoundaries = [
  'Billing and subscription upgrades are not implemented in the prototype.',
  'Production tenant onboarding is deferred.',
  'The current workspace stays mock-backed and safe by default.',
]

export const feedbackCategories = ['Workflow issue', 'Evidence clarity', 'Permission boundary', 'Visual bug', 'Documentation gap']

export const fallbackUtilityRoute = {
  description: 'This utility surface is not part of the primary workflow.',
  icon: FileQuestion,
  label: 'Utility',
  path: '/help',
  title: 'DataSentinel',
}
