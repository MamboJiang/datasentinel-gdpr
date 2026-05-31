import type { CSSProperties } from 'react'
import type { Signal, SourceReviewContextWindow, SourceReviewPreview } from '../types'
import { humanize } from './formatters'

export type EvidenceAnchor = {
  anchorId: string
  format: string
  label: string
  locationLabel: string
  contextWindow?: SourceReviewContextWindow
  pageRegionFocus?: PageRegionFocus
  selectorLabel: string
  redactedText: string
  detector: string
  confidence: number
  page: number
}

type AnchorSelector = NonNullable<Signal['evidenceAnchor']>['selector']
type PageRegion = NonNullable<NonNullable<AnchorSelector>['pageRegion']>
type PageRegionFocus = {
  boxStyle: CSSProperties
  frameStyle: CSSProperties
  kind: 'image' | 'pdf'
}

type SourcePreviewSummary = {
  anchorCount: number
  formatLabel: string
  pageCount: number
  rawBoundaryLabel: string
  redactionLabel: string
  structureCount: number
  tableCellCount: number
}

export function buildEvidenceAnchors(signals: Signal[] = []): EvidenceAnchor[] {
  return signals.map((signal, index) => {
    const contractAnchor = signal.evidenceAnchor
    const selector = contractAnchor?.selector
    const page = typeof selector?.page === 'number' ? selector.page : signal.page ?? 1

    return {
      anchorId: contractAnchor?.anchorId ?? `${signal.type}-${signal.detector}-${index}`,
      format: contractAnchor?.format ? humanize(contractAnchor.format) : 'Redacted signal',
      label: contractAnchor?.label ?? humanize(signal.type),
      locationLabel: contractAnchor?.fallback?.label ?? buildLocationLabel(selector, signal.page),
      contextWindow: undefined,
      pageRegionFocus: buildPageRegionFocus(selector?.pageRegion),
      selectorLabel: buildSelectorLabel(selector),
      redactedText: contractAnchor?.redactedText ?? contractAnchor?.fallback?.redactedText ?? signal.snippet,
      detector: humanize(signal.detector),
      confidence: signal.confidence,
      page,
    }
  })
}

export function attachPreviewContextWindows(anchors: EvidenceAnchor[], preview: SourceReviewPreview | undefined): EvidenceAnchor[] {
  if (!preview) {
    return anchors
  }
  const contextByAnchor = new Map<string, SourceReviewContextWindow>()
  for (const context of preview.contextWindows ?? []) {
    contextByAnchor.set(context.anchorId, context)
  }
  for (const anchor of preview.anchors ?? []) {
    if (anchor.contextWindow) {
      contextByAnchor.set(anchor.anchorId, anchor.contextWindow)
    }
  }
  if (contextByAnchor.size === 0) {
    return anchors
  }
  return anchors.map((anchor) => ({
    ...anchor,
    contextWindow: contextByAnchor.get(anchor.anchorId),
  }))
}

export function buildSourcePreviewSummary(preview: SourceReviewPreview | undefined): SourcePreviewSummary | null {
  if (!preview) {
    return null
  }
  return {
    anchorCount: preview.anchors?.length ?? 0,
    formatLabel: humanize(preview.fileFormat),
    pageCount: preview.pages?.length ?? 0,
    rawBoundaryLabel: preview.rawContentExposed || preview.pageImagesExposed ? 'Raw boundary open' : 'Raw boundary sealed',
    redactionLabel: humanize(preview.redactionMode),
    structureCount: preview.structureBlocks?.length ?? 0,
    tableCellCount: preview.tableCells?.length ?? 0,
  }
}

export function buildPreviewPageRegionFocus(
  preview: SourceReviewPreview | undefined,
  anchorId: string | undefined,
): PageRegionFocus | undefined {
  if (!preview || !anchorId) {
    return undefined
  }
  for (const page of preview.pages ?? []) {
    for (const region of page.regions ?? []) {
      if (region.anchorId === anchorId) {
        return buildPageRegionFocus(region.region)
      }
    }
  }
  return undefined
}

function buildLocationLabel(selector: AnchorSelector | undefined, fallbackPage?: number | null): string {
  if (selector && typeof selector === 'object' && 'frameIndex' in selector && typeof selector.frameIndex === 'number') {
    return `Frame ${selector.frameIndex}`
  }
  if (selector && typeof selector === 'object' && 'page' in selector && typeof selector.page === 'number') {
    return `Page ${selector.page}`
  }
  if (fallbackPage) {
    return `Page ${fallbackPage}`
  }
  if (selector && typeof selector === 'object' && 'type' in selector && selector.type === 'textPosition') {
    return 'Text position'
  }
  return 'Fallback location'
}

function buildSelectorLabel(selector: AnchorSelector | undefined): string {
  if (!selector || typeof selector !== 'object' || !('type' in selector) || typeof selector.type !== 'string') {
    return 'Fallback selector'
  }

  if (selector.type === 'textPosition') {
    if (selector.pageRegion && typeof selector.pageRegion === 'object') {
      return buildRegionLabel(selector.pageRegion)
    }
    if ('sourceStart' in selector && 'sourceEnd' in selector && typeof selector.sourceStart === 'number' && typeof selector.sourceEnd === 'number') {
      return `Page text ${selector.sourceStart}-${selector.sourceEnd}`
    }
    if ('start' in selector && 'end' in selector && typeof selector.start === 'number' && typeof selector.end === 'number') {
      return `Text ${selector.start}-${selector.end}`
    }
  }
  if (selector.type === 'tableCell') {
    const row = typeof selector.row === 'number' ? selector.row : null
    const column = typeof selector.columnLabel === 'string'
      ? selector.columnLabel
      : typeof selector.column === 'number' ? String(selector.column) : null
    const sheet = typeof selector.sheetName === 'string' ? `${selector.sheetName} ` : ''
    if (row && column) {
      return `${sheet}row ${row} column ${column}`
    }
  }
  if (selector.type === 'structurePath') {
    if (typeof selector.blockLabel === 'string' && selector.blockLabel) {
      return selector.blockLabel
    }
    if (typeof selector.slideNumber === 'number' && typeof selector.shapeIndex === 'number') {
      return `Slide ${selector.slideNumber} shape ${selector.shapeIndex}`
    }
    if (typeof selector.paragraphIndex === 'number') {
      return `Paragraph ${selector.paragraphIndex}`
    }
    if (typeof selector.tagName === 'string') {
      return `HTML ${selector.tagName}`
    }
  }

  return humanize(selector.type)
}

function buildRegionLabel(region: NonNullable<AnchorSelector>['pageRegion']): string {
  if (
    region
    && typeof region.x === 'number'
    && typeof region.y === 'number'
    && typeof region.width === 'number'
    && typeof region.height === 'number'
  ) {
    const unit = typeof region.unit === 'string' && region.unit ? region.unit : 'pt'
    const label = region.origin === 'top_left' || unit === 'px' ? 'Image region' : 'PDF region'
    return `${label} ${Math.round(region.x)},${Math.round(region.y)} ${Math.round(region.width)}x${Math.round(region.height)} ${unit}`
  }
  return 'Page region'
}

export function buildPageRegionFocus(region: PageRegion | undefined): PageRegionFocus | undefined {
  if (
    !region
    || typeof region.x !== 'number'
    || typeof region.y !== 'number'
    || typeof region.width !== 'number'
    || typeof region.height !== 'number'
    || region.width <= 0
    || region.height <= 0
  ) {
    return undefined
  }

  const kind = region.origin === 'top_left' || region.unit === 'px' ? 'image' : 'pdf'
  const pageWidth = positiveNumber(region.pageWidth) ?? defaultRegionPageWidth(region, kind)
  const pageHeight = positiveNumber(region.pageHeight) ?? defaultRegionPageHeight(region, kind)
  const top = region.origin === 'bottom_left' ? pageHeight - region.y - region.height : region.y
  const leftPercent = clampPercent((region.x / pageWidth) * 100)
  const topPercent = clampPercent((top / pageHeight) * 100)
  const widthPercent = clampPercent((region.width / pageWidth) * 100, 1, 100 - leftPercent)
  const heightPercent = clampPercent((region.height / pageHeight) * 100, 1, 100 - topPercent)

  return {
    boxStyle: {
      height: `${heightPercent}%`,
      left: `${leftPercent}%`,
      top: `${topPercent}%`,
      width: `${widthPercent}%`,
    },
    frameStyle: {
      aspectRatio: `${pageWidth} / ${pageHeight}`,
    },
    kind,
  }
}

function positiveNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : undefined
}

function defaultRegionPageWidth(region: PageRegion, kind: 'image' | 'pdf'): number {
  if (kind === 'pdf') {
    return 612
  }
  return Math.max((region.x ?? 0) + (region.width ?? 0) + 40, 320)
}

function defaultRegionPageHeight(region: PageRegion, kind: 'image' | 'pdf'): number {
  if (kind === 'pdf') {
    return 792
  }
  return Math.max((region.y ?? 0) + (region.height ?? 0) + 40, 240)
}

function clampPercent(value: number, min = 0, max = 100): number {
  if (!Number.isFinite(value)) {
    return min
  }
  return Math.min(Math.max(value, min), max)
}
