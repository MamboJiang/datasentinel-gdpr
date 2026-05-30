import { CheckCircle2, Database, Plus, ScanSearch } from 'lucide-react'
import { useData } from '../data/useData'
import { isSourceScanReady } from '../data/scanWorkflow'
import { humanize } from '../components/formatters'
import { Button, PageHeader, StatusBadge } from '../components/ui'

export function SourcesPage() {
  const { sources, scan, governanceConfig, startScan, testSourceConnection } = useData()
  const scanIsRunning = scan.status === 'running'

  return (
    <>
      <PageHeader
        eyebrow="Discovery inputs"
        title="Sources"
        actions={<Button icon={Plus}>Add source</Button>}
      />

      <section className="panel table-panel">
        <div className="table-summary">
          <div className="summary-icon"><Database aria-hidden="true" size={19} /></div>
          <div>
            <strong>{sources.length} configured sources</strong>
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
              {sources.map((source) => {
                const scanReady = isSourceScanReady(source, governanceConfig)

                return (
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
                        <button className="button button-ghost" type="button" onClick={() => testSourceConnection(source.sourceId)}>
                          <CheckCircle2 aria-hidden="true" size={16} /> Test connection
                        </button>
                        <button
                          className="button button-ghost"
                          disabled={!scanReady || scanIsRunning}
                          title={scanReady ? undefined : 'Scan requires a mock-ready source'}
                          type="button"
                          onClick={() => startScan({ scanType: 'full', sourceId: source.sourceId })}
                        >
                          <ScanSearch aria-hidden="true" size={16} /> Scan
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}
