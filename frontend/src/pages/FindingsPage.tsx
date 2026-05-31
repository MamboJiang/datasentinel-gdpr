import { FileSearch, Filter, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../data/useData'
import { humanize } from '../components/formatters'
import { safeFindingSourceLabel } from '../components/findingDisplay'
import { EmptyState, PageHeader, RiskBadge, StatusBadge } from '../components/ui'

export function FindingsPage() {
  const { findings } = useData()
  const [query, setQuery] = useState('')
  const [risk, setRisk] = useState('all')
  const [status, setStatus] = useState('all')

  const visibleFindings = useMemo(() => {
    return findings.filter((finding) => {
      const matchesQuery = `${finding.fileName} ${safeFindingSourceLabel(finding)} ${finding.contextCategory ?? ''}`.toLowerCase().includes(query.toLowerCase())
      const matchesRisk = risk === 'all' || finding.riskLevel === risk
      const matchesStatus = status === 'all' || finding.status === status
      return matchesQuery && matchesRisk && matchesStatus
    })
  }, [findings, query, risk, status])

  return (
    <>
      <PageHeader
        eyebrow="Accountable review"
        title="Findings"
      />

      <section className="panel table-panel">
        <div className="filter-bar">
          <label className="search-field">
            <Search aria-hidden="true" size={17} />
            <span className="sr-only">Search findings</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search file, source, or context" />
          </label>
          <div className="filter-selects">
            <Filter aria-hidden="true" size={17} />
            <label>
              <span className="sr-only">Risk level</span>
              <select value={risk} onChange={(event) => setRisk(event.target.value)}>
                <option value="all">All risks</option>
                <option value="high">High risk</option>
                <option value="medium">Medium risk</option>
                <option value="low">Low risk</option>
              </select>
            </label>
            <label>
              <span className="sr-only">Review status</span>
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="all">All statuses</option>
                <option value="open">Open</option>
                <option value="assigned">Assigned</option>
                <option value="delete_candidate">Deletion candidate</option>
                <option value="retained">Retained</option>
                <option value="false_positive">False positive</option>
                <option value="escalated">Escalated</option>
              </select>
            </label>
          </div>
        </div>

        {visibleFindings.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Finding</th>
                  <th>Evidence</th>
                  <th>Risk</th>
                  <th>Context</th>
                  <th>Retention</th>
                  <th>Owner</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {visibleFindings.map((finding) => (
                  <tr key={finding.findingId}>
                    <td>
                      <Link className="table-primary table-link" to={`/findings/${finding.findingId}`}>
                        <div className="file-avatar"><FileSearch aria-hidden="true" size={16} /></div>
                        <div><strong>{finding.fileName}</strong><span>{safeFindingSourceLabel(finding)}</span></div>
                      </Link>
                    </td>
                    <td>{finding.evidenceSignalCount ?? finding.personalDataTypes?.length ?? 0} signals</td>
                    <td><RiskBadge riskLevel={finding.riskLevel} score={finding.riskScore} /></td>
                    <td>{finding.contextCategory ? humanize(finding.contextCategory) : 'Unknown'}</td>
                    <td><StatusBadge value={finding.retentionStatus} /></td>
                    <td>
                      <div className="owner-cell">
                        <strong>{finding.owner?.displayName ?? 'Unassigned'}</strong>
                        <span>{finding.owner?.assignmentType ? humanize(finding.owner.assignmentType) : 'Unknown routing'}</span>
                      </div>
                    </td>
                    <td><StatusBadge value={finding.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState title="No findings match these filters" />}
      </section>
    </>
  )
}
