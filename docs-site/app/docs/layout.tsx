import type { ReactNode } from 'react'
import { DocsLayout } from 'fumadocs-ui/layouts/docs'
import { baseOptions, docsTree } from '@/lib/layout'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout tree={docsTree} {...baseOptions}>
      {children}
    </DocsLayout>
  )
}
