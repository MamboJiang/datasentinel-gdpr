import { CheckCircle2, Database, Plus, RotateCw, ScanSearch, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useData } from '../data/useData'
import { canStartDeltaScan, isSourceScanReady } from '../data/scanWorkflow'
import { humanize } from '../components/formatters'
import { Button, EmptyState, PageHeader, StatusBadge } from '../components/ui'
import { useI18n } from '../i18n'

export function SourcesPage() {
  const { t } = useI18n()
  const { sources, scan, governanceConfig, createSource, startScan, testSourceConnection } = useData()
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false)
  const scanIsRunning = scan.status === 'running'

  return (
    <>
      <PageHeader
        eyebrow="Discovery inputs"
        title="Sources"
        actions={<Button icon={Plus} onClick={() => setSourceDialogOpen(true)}>Add source</Button>}
      />

      <section className="panel table-panel">
        <div className="table-summary">
          <div className="summary-icon"><Database aria-hidden="true" size={19} /></div>
          <div>
            <strong>{t('{{count}} configured sources', { count: sources.length })}</strong>
          </div>
        </div>
        {sources.length ? <div className="table-wrap">
          <table className="source-table">
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
                        <div>
                          <strong>{source.name}</strong>
                          <span>{source.sourceId}</span>
                          {source.sampleFamilies?.length ? (
                            <small className="source-families">{source.sampleFamilies.join(', ')}</small>
                          ) : null}
                        </div>
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
        </div> : <EmptyState title="No sources configured" description="Add a local source, test the connection, then start a scan." />}
      </section>

      {sourceDialogOpen ? <SourceDialog onClose={() => setSourceDialogOpen(false)} onCreate={createSource} /> : null}
    </>
  )
}

function SourceDialog({
  onClose,
  onCreate,
}: {
  onClose: () => void
  onCreate: ReturnType<typeof useData>['createSource']
}) {
  const [name, setName] = useState('')
  const [rootPath, setRootPath] = useState('')
  const [ownerId, setOwnerId] = useState('')
  const canSubmit = name.trim().length > 1 && rootPath.trim().startsWith('/')

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }

    const normalizedName = name.trim()
    const normalizedRoot = rootPath.trim()
    onCreate({
      sourceId: `source_local_${Date.now()}`,
      name: normalizedName,
      sourceType: 'local_repo',
      status: 'registered',
      rootLabel: normalizedRoot,
      masterOfDataUserId: ownerId.trim() || undefined,
      config: { rootPath: normalizedRoot },
    })
    onClose()
  }

  return (
    <div className="dialog-overlay" role="presentation">
      <section aria-labelledby="source-dialog-title" aria-modal="true" className="dialog-card" role="dialog">
        <div className="dialog-header">
          <div>
            <p className="eyebrow">Source setup</p>
            <h2 id="source-dialog-title">Add local source</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Close source dialog" onClick={onClose}><X aria-hidden="true" size={18} /></button>
        </div>
        <form onSubmit={submit}>
          <label className="form-field">
            <span>Source name</span>
            <input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Finance shared folder" />
          </label>
          <label className="form-field">
            <span>Allowed absolute path</span>
            <input value={rootPath} onChange={(event) => setRootPath(event.target.value)} placeholder="/srv/datasentinel/sources/finance" />
          </label>
          <label className="form-field">
            <span>Master of Data user ID</span>
            <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} placeholder="Optional owner identifier" />
          </label>
          <div className="dialog-notice">
            <CheckCircle2 aria-hidden="true" size={17} />
            <span>The API server must be started with this path under an allowed root before the connection can pass.</span>
          </div>
          <div className="dialog-actions">
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button disabled={!canSubmit} type="submit">Register source</Button>
          </div>
        </form>
      </section>
    </div>
  )
}
