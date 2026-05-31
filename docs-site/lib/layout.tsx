import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared'
import { source } from './source'

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: 'DataSentinel User Guide',
  },
}

export const docsTree = source.pageTree
