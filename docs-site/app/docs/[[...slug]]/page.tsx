import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { createRelativeLink } from 'fumadocs-ui/mdx'
import { DocsLayout } from 'fumadocs-ui/layouts/docs'
import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
} from 'fumadocs-ui/layouts/docs/page'
import { getMDXComponents } from '@/components/mdx-components'
import { baseOptions, docsTree } from '@/lib/layout'
import { source } from '@/lib/source'

type PageProps = {
  params: Promise<{
    slug?: string[]
  }>
}

export default async function Page({ params }: PageProps) {
  const { slug } = await params
  const page = source.getPage(slug)

  if (!page) {
    notFound()
  }

  const MDX = page.data.body
  const isHome = !slug?.length
  const mdxComponents = getMDXComponents({ a: createRelativeLink(source, page) })

  if (isHome) {
    return (
      <main className="ld-home-shell">
        <MDX components={mdxComponents} />
      </main>
    )
  }

  return (
    <DocsLayout tree={docsTree} {...baseOptions}>
      <DocsPage toc={page.data.toc} full={page.data.full}>
        {page.data.full ? null : (
          <>
            <DocsTitle>{page.data.title}</DocsTitle>
            <DocsDescription>{page.data.description}</DocsDescription>
          </>
        )}
        <DocsBody>
          <MDX components={mdxComponents} />
        </DocsBody>
      </DocsPage>
    </DocsLayout>
  )
}

export function generateStaticParams() {
  return source.generateParams()
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const page = source.getPage(slug)

  if (!page) {
    notFound()
  }

  const isHome = !slug?.length

  return {
    title: isHome ? { absolute: page.data.title } : page.data.title,
    description: page.data.description,
  }
}
