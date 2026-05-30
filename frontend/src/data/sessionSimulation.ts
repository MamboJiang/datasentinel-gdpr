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

export const workspaceSimulation = {
  description: 'Privacy operations workspace',
  id: 'datasentinel-gdpr',
  name: 'DataSentinel GDPR',
  plan: 'Prelaunch',
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
    description: 'Review the signed-in account, workspace, roles, and permission boundary.',
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
    description: 'View the prelaunch platform status surface.',
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
    description: 'Review and clear the current DataSentinel session.',
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
    description: 'Use Dashboard or Sources to start a scan after a source is configured.',
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
    title: 'Google and GitHub sign-in',
    description: 'The console now uses a backend-owned prelaunch session before showing internal workflow data.',
  },
  {
    title: 'Local language preference',
    description: 'The account menu now stores an EU language preference and localizes core UI copy through frontend dictionaries.',
  },
  {
    title: 'Account menu utility routes',
    description: 'Account settings, feedback, docs, help, status, plan, and session-boundary pages now open from the account menu.',
  },
  {
    title: 'Homepage contract coverage',
    description: 'The public homepage explains workflow, source setup, evaluation, governance, and safe prototype boundaries.',
  },
  {
    title: 'Delta scan representation',
    description: 'The console can represent changed-file-only work after a completed full-scan baseline.',
  },
]

export const sessionBoundaries = [
  'Log out clears the DataSentinel first-party session cookie.',
  'Provider access tokens are not exposed to the browser.',
  'Log out does not revoke Google or GitHub consent; users manage provider access in the provider account settings.',
  'Authentication does not grant real deletion, tenant, source connector, or production authorization powers.',
]

export const planBoundaries = [
  'Billing and subscription upgrades are not implemented in the prototype.',
  'Production tenant onboarding is deferred.',
  'The current workspace keeps deletion disabled and source boundaries explicit.',
]

export const feedbackCategories = ['Workflow issue', 'Evidence clarity', 'Permission boundary', 'Visual bug', 'Documentation gap']

export const fallbackUtilityRoute = {
  description: 'This utility surface is not part of the primary workflow.',
  icon: FileQuestion,
  label: 'Utility',
  path: '/help',
  title: 'DataSentinel',
}
