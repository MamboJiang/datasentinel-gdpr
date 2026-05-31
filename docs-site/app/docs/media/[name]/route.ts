import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { NextResponse } from 'next/server'

const screenshots = new Set([
  'audit-trail.png',
  'dashboard-overview.png',
  'evaluation-metrics.png',
  'findings-list.png',
  'sources-list.png',
])

type RouteContext = {
  params: Promise<{
    name: string
  }>
}

export async function GET(_request: Request, { params }: RouteContext) {
  const { name } = await params

  if (!screenshots.has(name)) {
    return new NextResponse(null, { status: 404 })
  }

  const file = await readFile(path.join(process.cwd(), 'public', 'images', 'docs', name))

  return new NextResponse(file, {
    headers: {
      'Cache-Control': 'public, max-age=31536000, immutable',
      'Content-Type': 'image/png',
    },
  })
}
