import { FileText, Highlighter, LocateFixed, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'
import type { Finding, Signal } from '../types'
import { safeFindingSourceLabel } from './findingDisplay'
import { humanize } from './formatters'
import { RiskBadge } from './ui'

type EvidenceAnchor = {
  anchorId: string
  label: string
  locationLabel: string
  redactedText: string
  detector: string
  confidence: number
  page: number
}

function buildEvidenceAnchors(signals: Signal[] = []): EvidenceAnchor[] {
  return signals.map((signal, index) => ({
    anchorId: `${signal.type}-${signal.detector}-${index}`,
    label: humanize(signal.type),
    locationLabel: signal.page ? `Page ${signal.page}` : 'Fallback location',
    redactedText: signal.snippet,
    detector: humanize(signal.detector),
    confidence: signal.confidence,
    page: signal.page ?? 1,
  }))
}

export function FileReviewEditor({
  finding,
  initialSignalIndex = 0,
  onClose,
}: {
  finding: Finding
  initialSignalIndex?: number
  onClose: () => void
}) {
  const anchors = buildEvidenceAnchors(finding.signals)
  const [activeIndex, setActiveIndex] = useState(Math.min(initialSignalIndex, Math.max(anchors.length - 1, 0)))
  const activeAnchor = anchors[activeIndex]

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
              <span>{activeAnchor?.detector ?? 'No detector'}</span>
            </div>

            <div className="document-page" aria-label="Redacted file preview">
              <div className="document-page-header">
                <span>{finding.contextCategory ? humanize(finding.contextCategory) : 'Document context'}</span>
                <span>Page {activeAnchor?.page ?? 1}</span>
              </div>
              <div className="document-lines">
                {anchors.map((anchor, index) => (
                  <button
                    className={`document-highlight ${index === activeIndex ? 'document-highlight-active' : ''}`}
                    key={anchor.anchorId}
                    onClick={() => setActiveIndex(index)}
                    type="button"
                  >
                    <Highlighter aria-hidden="true" size={15} />
                    <span>{anchor.redactedText}</span>
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
