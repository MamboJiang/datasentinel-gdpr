import { CheckCircle2, Database, Plus, RadioTower, ScanSearch } from 'lucide-react'
import { useData } from '../data/useData'
import { humanize } from '../components/formatters'
import { Button, PageHeader, StatusBadge } from '../components/ui'

export function SourcesPage() {
  const { sources, startScan } = useData()

  return (
    <>
      <PageHeader
        eyebrow="Discovery inputs"
        title="Sources"
        description="Manage the controlled repositories used for contract-backed GDPR discovery."
        actions={<Button icon={Plus}>Add source</Button>}
      />

      <section className="panel table-panel">
        <div className="table-summary">
          <div className="summary-icon"><Database aria-hidden="true" size={19} /></div>
          <div>
            <strong>{sources.length} configured sources</strong>
            <span>Local and mocked connectors only in this prototype.</span>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Type</th>
                <th>Status</th>
                <th>Root label</th>
                <th>Master of data</th>
                <th><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.sourceId}>
                  <td>
                    <div className="table-primary">
                      <div className="file-avatar"><Database aria-hidden="true" size={16} /></div>
                      <div><strong>{source.name}</strong><span>{source.sourceId}</span></div>
                    </div>
                  </td>
                  <td>{humanize(source.sourceType)}</td>
                  <td><StatusBadge value={source.status} /></td>
                  <td>{source.rootLabel ?? 'Not available'}</td>
                  <td>{source.masterOfDataUserId ?? 'Unassigned'}</td>
                  <td>
                    <div className="row-actions">
                      <button type="button"><CheckCircle2 aria-hidden="true" size={16} /> Test connection</button>
                      <button type="button" onClick={() => startScan('full')}><ScanSearch aria-hidden="true" size={16} /> Scan</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="info-panel">
        <RadioTower aria-hidden="true" size={19} />
        <div>
          <strong>External integrations are intentionally deferred</strong>
          <p>P0 does not connect to production Microsoft Graph, OAuth tenants, or remote deletion APIs.</p>
        </div>
      </div>
    </>
  )
}
