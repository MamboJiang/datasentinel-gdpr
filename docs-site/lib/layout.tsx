import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared'
import { source } from './source'

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: 'DataSentinel User Guide',
  },
  links: [
    {
      text: 'Dashboard',
      url: '/docs/dashboard-and-scans',
    },
    {
      text: 'Safety',
      url: '/docs/safety-and-boundaries',
    },
  ],
}

export const docsTree = source.pageTree
