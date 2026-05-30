import { CheckCircle2, Database, Plus, RotateCw, ScanSearch } from 'lucide-react'
import { useData } from '../data/useData'
import { canStartDeltaScan, isSourceScanReady } from '../data/scanWorkflow'
import { humanize } from '../components/formatters'
import { Button, PageHeader, StatusBadge } from '../components/ui'
import { useI18n } from '../i18n'

export function SourcesPage() {
  const { t } = useI18n()
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
            <strong>{t('{{count}} configured sources', { count: sources.length })}</strong>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t('Source')}</th>
                <th>{t('Type')}</th>
                <th>{t('Status')}</th>
                <th>{t('Root label')}</th>
                <th>{t('Master of data')}</th>
                <th><span className="sr-only">{t('Actions')}</span></th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => {
                const scanReady = isSourceScanReady(source, governanceConfig)
                const deltaReady = scanReady && !scanIsRunning && canStartDeltaScan(scan, source.sourceId)

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
                    <td>{source.rootLabel ?? t('Not available')}</td>
                    <td>{source.masterOfDataUserId ?? t('Unassigned')}</td>
                    <td>
                      <div className="row-actions">
                        <button className="button button-ghost" type="button" onClick={() => testSourceConnection(source.sourceId)}>
                          <CheckCircle2 aria-hidden="true" size={16} /> {t('Test connection')}
                        </button>
                        <button
                          className="button button-ghost"
                          disabled={!scanReady || scanIsRunning}
                          title={scanReady ? undefined : t('Scan requires a mock-ready source')}
                          type="button"
                          onClick={() => startScan({ scanType: 'full', sourceId: source.sourceId })}
                        >
                          <ScanSearch aria-hidden="true" size={16} /> {t('Full scan')}
                        </button>
                        <button
                          className="button button-ghost"
                          disabled={!deltaReady}
                          title={deltaReady ? undefined : t('Delta scan requires a completed full-scan baseline')}
                          type="button"
                          onClick={() => startScan({ baselineScanId: scan.deltaScan?.baselineScanId ?? scan.scanId, scanType: 'delta', sourceId: source.sourceId })}
                        >
                          <RotateCw aria-hidden="true" size={16} /> {t('Delta scan')}
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
