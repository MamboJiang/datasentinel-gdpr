import { CheckCircle2, Database, FileText, Pencil, Plus, RotateCw, ScanSearch, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useData } from '../data/useData'
import { canStartDeltaScan } from '../data/scanWorkflow'
import { canStartSourceScan, sourceDisplayStatus, sourceScanBlockReason } from '../data/sourceScanReadiness'
import { humanize } from '../components/formatters'
import { Button, EmptyState, PageHeader, StatusBadge } from '../components/ui'
import { SourceDialog } from '../components/SourceDialog'
import { useI18n } from '../i18n'
import type { Source } from '../types'
import { SUPPORTED_FILE_TYPES, SUPPORTED_FILE_TYPES_DESCRIPTION, SUPPORTED_FILE_TYPES_NOTE } from './sourceSupportContent'

export function SourcesPage() {
  const { t } = useI18n()
  const { sources, scan, governanceConfig, createSource, deleteSource, googleDriveBinding, runtimeAuthorizedSourceIds, startScan, testSourceConnection, updateSource, workspaceAdmin } = useData()
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false)
  const [editingSource, setEditingSource] = useState<Source | null>(null)
  const scanIsRunning = scan.status === 'running'

  return (
    <>
      <PageHeader
        eyebrow="Discovery inputs"
        title="Sources"
        actions={<Button icon={Plus} onClick={() => {
          setEditingSource(null)
          setSourceDialogOpen(true)
        }}>Add source</Button>}
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
                <th>{t('Source owner')}</th>
                <th><span className="sr-only">{t('Actions')}</span></th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => {
                const googleDriveBindingConnected = Boolean(googleDriveBinding?.connected)
                const scanReady = canStartSourceScan(source, governanceConfig, runtimeAuthorizedSourceIds, googleDriveBindingConnected)
                const deltaReady = scanReady && !scanIsRunning && canStartDeltaScan(scan, source.sourceId)
                const scanBlockReason = sourceScanBlockReason(source, governanceConfig, runtimeAuthorizedSourceIds, googleDriveBindingConnected)

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
                    <td><StatusBadge value={sourceDisplayStatus(source, runtimeAuthorizedSourceIds, googleDriveBindingConnected)} /></td>
                    <td>{source.rootLabel ?? t('Not available')}</td>
                    <td>{sourceOwnerLabel(source, t)}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="button button-ghost"
                          type="button"
                          onClick={() => {
                            setEditingSource(source)
                            setSourceDialogOpen(true)
                          }}
                        >
                          <Pencil aria-hidden="true" size={16} /> {t('Edit')}
                        </button>
                        <button className="button button-ghost" type="button" onClick={() => testSourceConnection(source.sourceId)}>
                          <CheckCircle2 aria-hidden="true" size={16} /> {t('Test connection')}
                        </button>
                        <button
                          className="button button-ghost"
                          disabled={!scanReady || scanIsRunning}
                          title={scanReady ? undefined : t(scanBlockReason ?? 'Scan requires a connected source')}
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

      <section className="supported-formats" aria-labelledby="supported-file-types-title">
        <div className="supported-formats-heading">
          <FileText aria-hidden="true" size={18} />
          <div>
            <h2 id="supported-file-types-title">{t('Supported file types')}</h2>
            <p>{t(SUPPORTED_FILE_TYPES_DESCRIPTION)}</p>
          </div>
        </div>
        <div className="supported-format-list" aria-label={t('Currently supported file types')}>
          {SUPPORTED_FILE_TYPES.map((type) => <span key={type}>{t(type)}</span>)}
        </div>
        <p className="supported-formats-note">
          {t(SUPPORTED_FILE_TYPES_NOTE)}
        </p>
      </section>

      {sourceDialogOpen ? (
        <SourceDialog
          members={workspaceAdmin.members}
          onClose={() => setSourceDialogOpen(false)}
          onCreate={createSource}
          onUpdate={updateSource}
          source={editingSource}
          googleDriveBinding={googleDriveBinding}
        />
      ) : null}
    </>
  )
}

function sourceOwnerLabel(source: Source, t: (value: string) => string): string {
  if (source.assignedOwner?.displayName) {
    return source.assignedOwner.displayName
  }
  if (source.assignedOwnerUserId) {
    return source.assignedOwnerUserId
  }
  if (source.fallbackOwner?.displayName) {
    return `${source.fallbackOwner.displayName} (${t('fallback')})`
  }
  if (source.masterOfDataUserId) {
    return source.masterOfDataUserId
  }
  return t('Unassigned')
}
