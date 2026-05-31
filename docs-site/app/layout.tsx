import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { RootProvider } from 'fumadocs-ui/provider/next'
import './global.css'

export const metadata: Metadata = {
  title: {
    default: 'DataSentinel User Guide',
    template: '%s | DataSentinel User Guide',
  },
  description: 'Task-oriented user documentation for the DataSentinel GDPR discovery prototype.',
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <RootProvider search={{ options: { api: '/docs/api/search' } }}>{children}</RootProvider>
      </body>
    </html>
  )
}
