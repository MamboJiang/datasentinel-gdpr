import { CheckCircle2, Cloud, Database, FolderOpen, Link2, Plus, RotateCw, ScanSearch, Trash2, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { useData } from '../data/useData'
import { canStartDeltaScan, isSourceScanReady } from '../data/scanWorkflow'
import { pickGoogleDriveItems, type GoogleDrivePickedItem, type GoogleDrivePickerMode } from '../data/googleDrivePicker'
import { humanize } from '../components/formatters'
import { Button, EmptyState, PageHeader, StatusBadge } from '../components/ui'
import { loadGoogleDrivePickerConfig, type GoogleDrivePickerConfig } from '../data/serverApi'
import { useI18n } from '../i18n'

export function SourcesPage() {
  const { t } = useI18n()
  const { sources, scan, governanceConfig, createSource, deleteSource, startScan, testSourceConnection } = useData()
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
                          title={scanReady ? undefined : t('Scan requires a connected source')}
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
                        <button
                          className="button button-ghost"
                          disabled={scanIsRunning}
                          title={scanIsRunning ? t('Source deletion is disabled while a scan is running') : t('Delete source registration')}
                          type="button"
                          onClick={() => {
                            if (window.confirm(t('Delete this source registration? Source files are not deleted.'))) {
                              deleteSource(source.sourceId)
                            }
                          }}
                        >
                          <Trash2 aria-hidden="true" size={16} /> {t('Delete')}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div> : <EmptyState title="No sources configured" description="Add Google Drive, a direct HTTPS file link, or an allowed local path, then start a scan." />}
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
  const [mode, setMode] = useState<'drive' | 'local' | 'remote'>('remote')
  const [name, setName] = useState('')
  const [rootPath, setRootPath] = useState('')
  const [remoteUrl, setRemoteUrl] = useState('')
  const [ownerId, setOwnerId] = useState('')
  const [driveConfig, setDriveConfig] = useState<GoogleDrivePickerConfig | null>(null)
  const [driveItems, setDriveItems] = useState<GoogleDrivePickedItem[]>([])
  const [driveAccessToken, setDriveAccessToken] = useState<string | undefined>()
  const [driveError, setDriveError] = useState<string | null>(null)
  const [driveLoading, setDriveLoading] = useState(false)
  const canSubmit = canSubmitSource(mode, name, rootPath, remoteUrl, driveItems, driveAccessToken)

  useEffect(() => {
    let active = true
    loadGoogleDrivePickerConfig()
      .then((result) => {
        if (active) {
          setDriveConfig(result.data)
        }
      })
      .catch((error) => {
        if (active) {
          setDriveError(error instanceof Error ? error.message : 'Google Drive setup could not be checked.')
        }
      })
    return () => {
      active = false
    }
  }, [])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }

    const normalizedName = name.trim()
    const normalizedOwner = ownerId.trim() || undefined

    if (mode === 'remote') {
      const normalizedUrl = remoteUrl.trim()
      onCreate({
        sourceId: `source_remote_${Date.now()}`,
        name: normalizedName,
        sourceType: 'remote_file_link',
        rootLabel: normalizedUrl,
        masterOfDataUserId: normalizedOwner,
        config: { url: normalizedUrl },
      })
      onClose()
      return
    }

    if (mode === 'drive') {
      onCreate({
        googleDriveAccessToken: driveAccessToken,
        sourceId: `source_drive_${Date.now()}`,
        name: normalizedName,
        sourceType: 'google_drive_selection',
        rootLabel: driveItems.map((item) => item.name).join(', '),
        masterOfDataUserId: normalizedOwner,
        config: { items: driveItems },
      })
      onClose()
      return
    }

    const normalizedRoot = rootPath.trim()
    onCreate({
      sourceId: `source_local_${Date.now()}`,
      name: normalizedName,
      sourceType: 'local_repo',
      status: 'registered',
      rootLabel: normalizedRoot,
      masterOfDataUserId: normalizedOwner,
      config: { rootPath: normalizedRoot },
    })
    onClose()
  }

  async function chooseDriveItems(pickerMode: GoogleDrivePickerMode) {
    if (!driveConfig) {
      return
    }

    setDriveLoading(true)
    setDriveError(null)
    try {
      const result = await pickGoogleDriveItems(driveConfig, pickerMode)
      if (!result.items.length) {
        return
      }
      setDriveItems(result.items)
      setDriveAccessToken(result.accessToken)
      if (!name.trim()) {
        setName(result.items.length === 1 ? result.items[0].name : `Google Drive selection (${result.items.length})`)
      }
    } catch (error) {
      setDriveError(error instanceof Error ? error.message : 'Google Drive Picker failed.')
    } finally {
      setDriveLoading(false)
    }
  }

  return (
    <div className="dialog-overlay" role="presentation">
      <section aria-labelledby="source-dialog-title" aria-modal="true" className="dialog-card" role="dialog">
        <div className="dialog-header">
          <div>
            <p className="eyebrow">Source setup</p>
            <h2 id="source-dialog-title">Add source</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Close source dialog" onClick={onClose}><X aria-hidden="true" size={18} /></button>
        </div>
        <form onSubmit={submit}>
          <div className="segmented-control" role="tablist" aria-label="Source type">
            <button className={mode === 'remote' ? 'active' : ''} type="button" onClick={() => setMode('remote')}><Link2 aria-hidden="true" size={16} /> Direct link</button>
            <button className={mode === 'drive' ? 'active' : ''} type="button" onClick={() => setMode('drive')}><Cloud aria-hidden="true" size={16} /> Google Drive</button>
            <button className={mode === 'local' ? 'active' : ''} type="button" onClick={() => setMode('local')}><Database aria-hidden="true" size={16} /> Local path</button>
          </div>
          <label className="form-field">
            <span>Source name</span>
            <input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Name this source" />
          </label>
          {mode === 'remote' ? (
            <label className="form-field">
              <span>HTTPS file URL</span>
              <input value={remoteUrl} onChange={(event) => setRemoteUrl(event.target.value)} placeholder="Paste an HTTPS file URL" />
            </label>
          ) : null}
          {mode === 'drive' ? (
            <div className="dialog-stack">
              <div className="drive-actions">
                <button className="button button-ghost" disabled={!driveConfig?.configured || driveLoading} type="button" onClick={() => chooseDriveItems('files')}>
                  <Cloud aria-hidden="true" size={16} /> Choose files
                </button>
                <button className="button button-ghost" disabled={!driveConfig?.configured || driveLoading} type="button" onClick={() => chooseDriveItems('folders')}>
                  <FolderOpen aria-hidden="true" size={16} /> Choose folder
                </button>
              </div>
              {driveItems.length ? (
                <div className="dialog-selection">
                  {driveItems.map((item) => <span key={item.id}>{item.name}</span>)}
                </div>
              ) : null}
              {!driveConfig?.configured ? (
                <div className="dialog-notice">
                  <Cloud aria-hidden="true" size={17} />
                  <span>Google Drive Picker needs host config: {driveConfig?.missing.join(', ') || 'Google public credentials'}.</span>
                </div>
              ) : null}
              {driveError ? <p className="form-error">{driveError}</p> : null}
            </div>
          ) : null}
          {mode === 'local' ? (
            <label className="form-field">
              <span>Allowed absolute path</span>
              <input value={rootPath} onChange={(event) => setRootPath(event.target.value)} placeholder="Enter an allowed absolute path" />
            </label>
          ) : null}
          <label className="form-field">
            <span>Master of Data user ID</span>
            <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} placeholder="Optional owner identifier" />
          </label>
          <div className="dialog-notice">
            <CheckCircle2 aria-hidden="true" size={17} />
            <span>DataSentinel reads source content only during scan and stores metadata, redacted evidence, findings, and audit events.</span>
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

function canSubmitSource(
  mode: 'drive' | 'local' | 'remote',
  name: string,
  rootPath: string,
  remoteUrl: string,
  driveItems: GoogleDrivePickedItem[],
  driveAccessToken?: string,
) {
  if (name.trim().length < 2) {
    return false
  }
  if (mode === 'local') {
    return rootPath.trim().startsWith('/')
  }
  if (mode === 'remote') {
    return remoteUrl.trim().startsWith('https://')
  }
  return driveItems.length > 0 && Boolean(driveAccessToken)
}
