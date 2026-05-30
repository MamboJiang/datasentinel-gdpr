import { Activity, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useData } from '../data/useData'
import { formatDate, humanize } from '../components/formatters'
import { EmptyState, PageHeader, StatusBadge } from '../components/ui'

export function AuditPage() {
  const { auditEvents } = useData()
  const [query, setQuery] = useState('')

  const visibleEvents = useMemo(() => {
    return auditEvents.filter((event) => [
      event.eventType,
      event.actorId,
      event.actorType,
      event.action,
      event.outcome,
      event.objectType,
      event.objectId,
      event.summary,
      event.findingId,
      event.scanId,
    ].join(' ').toLowerCase().includes(query.toLowerCase()))
  }, [auditEvents, query])

  return (
    <>
      <PageHeader
        eyebrow="Accountability record"
        title="Audit trail"
      />

      <section className="panel table-panel">
        <div className="filter-bar">
          <label className="search-field">
            <Search aria-hidden="true" size={17} />
            <span className="sr-only">Search audit trail</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search event, actor, or finding" />
          </label>
          <span className="result-count">{visibleEvents.length} visible events</span>
        </div>
        {visibleEvents.length ? (
          <div className="audit-list">
            {visibleEvents.map((event) => (
              <article className="audit-row" key={event.auditEventId}>
                <div className="audit-icon"><Activity aria-hidden="true" size={17} /></div>
                <div className="audit-main">
                  <div><strong>{humanize(event.action ?? event.eventType)}</strong><StatusBadge value={event.resultingStatus ?? event.outcome} /></div>
                  <p>{event.summary ?? 'No event summary is available.'}</p>
                  {event.reason ? <small>Reason: {event.reason}</small> : null}
                  <small>{humanize(event.objectType ?? 'event')} · {event.objectId ?? event.findingId ?? event.scanId ?? 'system'} · {event.evidenceReferences?.length ?? 0} evidence refs</small>
                </div>
                <div className="audit-meta">
                  <strong>{event.actorId}</strong>
                  <span>{formatDate(event.occurredAt)}</span>
                  <span>{humanize(event.actorType ?? 'unknown actor')}</span>
                  <span>{event.findingId ?? event.scanId ?? 'System event'}</span>
                </div>
              </article>
            ))}
          </div>
        ) : <EmptyState title="No audit events match this search" />}
      </section>
    </>
  )
}
