import { FileText, Highlighter, LocateFixed, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'
import type { Finding, SourceReviewContextWindow } from '../types'
import { safeFindingSourceLabel } from './findingDisplay'
import { humanize } from './formatters'
import { attachPreviewContextWindows, buildEvidenceAnchors, buildPreviewPageRegionFocus, buildSourcePreviewSummary } from './fileReviewEditorModel'
import { RiskBadge } from './ui'
import './FileReviewEditor.css'

export function FileReviewEditor({
  finding,
  initialSignalIndex = 0,
  onClose,
}: {
  finding: Finding
  initialSignalIndex?: number
  onClose: () => void
}) {
  const anchors = attachPreviewContextWindows(buildEvidenceAnchors(finding.signals), finding.sourceReviewPreview)
  const [activeIndex, setActiveIndex] = useState(Math.min(initialSignalIndex, Math.max(anchors.length - 1, 0)))
  const activeAnchor = anchors[activeIndex]
  const previewSummary = buildSourcePreviewSummary(finding.sourceReviewPreview)
  const activeRegionFocus = buildPreviewPageRegionFocus(finding.sourceReviewPreview, activeAnchor?.anchorId) ?? activeAnchor?.pageRegionFocus

  return (
    <div className="file-editor-overlay" role="presentation">
      <section aria-labelledby="file-editor-title" aria-modal="true" className="file-editor" role="dialog">
        <header className="file-editor-header">
          <div>
            <p className="eyebrow">File review</p>
            <h2 id="file-editor-title">{finding.fileName}</h2>
            <span>{safeFindingSourceLabel(finding)}</span>
          </div>
          <div className="file-editor-header-actions">
            <RiskBadge riskLevel={finding.riskLevel} score={finding.riskScore} />
            <button className="icon-button" type="button" aria-label="Close file review" onClick={onClose}>
              <X aria-hidden="true" size={18} />
            </button>
          </div>
        </header>

        <div className="file-editor-body">
          <aside className="evidence-rail" aria-label="Sensitive evidence anchors">
            <div className="evidence-rail-header">
              <FileText aria-hidden="true" size={18} />
              <div>
                <strong>Evidence anchors</strong>
              </div>
            </div>
            {anchors.length > 0 ? (
              <div className="evidence-anchor-list">
                {anchors.map((anchor, index) => (
                  <button
                    className={`evidence-anchor ${index === activeIndex ? 'evidence-anchor-active' : ''}`}
                    key={anchor.anchorId}
                    onClick={() => setActiveIndex(index)}
                    type="button"
                  >
                    <span>
                      <strong>{anchor.label}</strong>
                      <small>{anchor.locationLabel} · {Math.round(anchor.confidence * 100)}%</small>
                    </span>
                    <LocateFixed aria-hidden="true" size={16} />
                  </button>
                ))}
              </div>
            ) : (
              <p className="editor-empty">No redacted evidence anchors are available.</p>
            )}
          </aside>

          <main className="document-review-pane">
            <div className="document-toolbar">
              <span>{activeAnchor?.locationLabel ?? 'No location'}</span>
              <span>{activeAnchor ? `${activeAnchor.detector} · ${activeAnchor.format}` : 'No detector'}</span>
            </div>
            {previewSummary ? (
              <div className="source-preview-summary" aria-label="Redacted source preview package">
                <span>{previewSummary.formatLabel}</span>
                <span>{previewSummary.redactionLabel}</span>
                <span>{previewSummary.anchorCount} anchors</span>
                <span>{previewSummary.pageCount} pages</span>
                <span>{previewSummary.tableCellCount} cells</span>
                <span>{previewSummary.structureCount} blocks</span>
                <span>{previewSummary.rawBoundaryLabel}</span>
              </div>
            ) : null}

            <div className="document-page" aria-label="Redacted file preview">
              <div className="document-page-header">
                <span>{finding.contextCategory ? humanize(finding.contextCategory) : 'Document context'}</span>
                <span>Page {activeAnchor?.page ?? 1}</span>
              </div>
              {activeRegionFocus ? (
                <div className="document-region-map" aria-label="Source-derived region focus">
                  <div
                    className={`document-region-frame document-region-${activeRegionFocus.kind}`}
                    style={activeRegionFocus.frameStyle}
                  >
                    <button
                      aria-label={`Focused source region: ${activeAnchor.selectorLabel}`}
                      className="document-region-box"
                      style={activeRegionFocus.boxStyle}
                      type="button"
                    >
                      <span>{activeAnchor.redactedText}</span>
                    </button>
                  </div>
                </div>
              ) : null}
              {activeAnchor?.contextWindow ? (
                <RedactedContextWindow context={activeAnchor.contextWindow} />
              ) : null}
              <div className="document-lines">
                {anchors.map((anchor, index) => (
                  <button
                    className={`document-highlight ${index === activeIndex ? 'document-highlight-active' : ''}`}
                    key={anchor.anchorId}
                    onClick={() => setActiveIndex(index)}
                    type="button"
                  >
                    <Highlighter aria-hidden="true" size={15} />
                    <span>
                      <strong>{anchor.locationLabel} · {anchor.selectorLabel}</strong>
                      <small>{anchor.redactedText}</small>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="editor-safety-note">
              <ShieldCheck aria-hidden="true" size={17} />
              <span>Read-only redacted preview</span>
            </div>
          </main>
        </div>
      </section>
    </div>
  )
}

function RedactedContextWindow({ context }: { context: SourceReviewContextWindow }) {
  const text = context.redactedContext
  const start = typeof context.highlightStart === 'number' ? context.highlightStart : -1
  const end = typeof context.highlightEnd === 'number' ? context.highlightEnd : -1
  const canHighlight = start >= 0 && end > start && end <= text.length

  return (
    <div className="document-context-window" aria-label="Redacted source context window">
      <div>
        <strong>Redacted source context</strong>
        <span>{context.rawContentExposed ? 'Raw boundary open' : 'Raw boundary sealed'}</span>
      </div>
      <p>
        {canHighlight ? (
          <>
            {text.slice(0, start)}
            <mark>{text.slice(start, end)}</mark>
            {text.slice(end)}
          </>
        ) : text}
      </p>
    </div>
  )
}
