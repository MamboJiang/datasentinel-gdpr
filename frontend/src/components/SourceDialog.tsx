import { CheckCircle2, Cloud, Database, FolderOpen, Link2, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { pickGoogleDriveItems, type GoogleDrivePickedItem, type GoogleDrivePickerMode } from '../data/googleDrivePicker'
import { loadGoogleDrivePickerToken, type GoogleDriveBinding } from '../data/authApi'
import { loadGoogleDrivePickerConfig, type GoogleDrivePickerConfig } from '../data/serverApi'
import { useData } from '../data/useData'
import type { Source } from '../types'
import { Button } from './ui'

type SourceDialogProps = {
  members: ReturnType<typeof useData>['workspaceAdmin']['members']
  onClose: () => void
  onCreate: ReturnType<typeof useData>['createSource']
  onUpdate: ReturnType<typeof useData>['updateSource']
  source: Source | null
  googleDriveBinding: GoogleDriveBinding | null
}

export function SourceDialog({
  members,
  onClose,
  onCreate,
  onUpdate,
  source,
  googleDriveBinding,
}: SourceDialogProps) {
  const editing = Boolean(source)
  const [mode, setMode] = useState<'drive' | 'local' | 'remote'>('remote')
  const [name, setName] = useState(source?.name ?? '')
  const [rootPath, setRootPath] = useState('')
  const [remoteUrl, setRemoteUrl] = useState('')
  const [ownerId, setOwnerId] = useState(source?.assignedOwnerUserId ?? source?.assignedOwner?.userId ?? '')
  const [driveConfig, setDriveConfig] = useState<GoogleDrivePickerConfig | null>(null)
  const [driveItems, setDriveItems] = useState<GoogleDrivePickedItem[]>([])
  const [driveAccessToken, setDriveAccessToken] = useState<string | undefined>()
  const [driveError, setDriveError] = useState<string | null>(null)
  const [driveLoading, setDriveLoading] = useState(false)
  const canSubmit = editing ? name.trim().length >= 2 : canSubmitSource(mode, name, rootPath, remoteUrl, driveItems, driveAccessToken)

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
    const normalizedOwner = ownerId.trim() || null

    if (source) {
      onUpdate({
        assignedOwnerUserId: normalizedOwner,
        name: normalizedName,
        sourceId: source.sourceId,
      })
      onClose()
      return
    }

    if (mode === 'remote') {
      const normalizedUrl = remoteUrl.trim()
      onCreate({
        sourceId: `source_remote_${Date.now()}`,
        name: normalizedName,
        sourceType: 'remote_file_link',
        rootLabel: normalizedUrl,
        assignedOwnerUserId: normalizedOwner,
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
        assignedOwnerUserId: normalizedOwner,
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
      assignedOwnerUserId: normalizedOwner,
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
      const boundToken = googleDriveBinding?.connected ? await loadGoogleDrivePickerToken() : null
      const result = await pickGoogleDriveItems(
        driveConfig,
        pickerMode,
        boundToken ? { accessToken: boundToken.accessToken } : {},
      )
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
            <h2 id="source-dialog-title">{editing ? 'Edit source' : 'Add source'}</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Close source dialog" onClick={onClose}><X aria-hidden="true" size={18} /></button>
        </div>
        <form onSubmit={submit}>
          {!editing ? <div className="segmented-control" role="tablist" aria-label="Source type">
            <button className={mode === 'remote' ? 'active' : ''} type="button" onClick={() => setMode('remote')}><Link2 aria-hidden="true" size={16} /> Direct link</button>
            <button className={mode === 'drive' ? 'active' : ''} type="button" onClick={() => setMode('drive')}><Cloud aria-hidden="true" size={16} /> Google Drive</button>
            <button className={mode === 'local' ? 'active' : ''} type="button" onClick={() => setMode('local')}><Database aria-hidden="true" size={16} /> Local path</button>
          </div> : null}
          <label className="form-field">
            <span>Source name</span>
            <input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Name this source" />
          </label>
          {!editing && mode === 'remote' ? (
            <label className="form-field">
              <span>HTTPS file URL</span>
              <input value={remoteUrl} onChange={(event) => setRemoteUrl(event.target.value)} placeholder="Paste an HTTPS file URL" />
            </label>
          ) : null}
          {!editing && mode === 'drive' ? (
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
          {!editing && mode === 'local' ? (
            <label className="form-field">
              <span>Allowed absolute path</span>
              <input value={rootPath} onChange={(event) => setRootPath(event.target.value)} placeholder="Enter an allowed absolute path" />
            </label>
          ) : null}
          <label className="form-field">
            <span>Source owner</span>
            <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
              <option value="">No direct owner</option>
              {members.map((member) => (
                <option key={member.membershipId} value={member.accountId}>
                  {member.displayName}{member.email ? ` - ${member.email}` : ''}
                </option>
              ))}
            </select>
          </label>
          <div className="dialog-notice">
            <CheckCircle2 aria-hidden="true" size={17} />
            <span>lawdit reads source content only during scan and stores metadata, redacted evidence, findings, and audit events.</span>
          </div>
          <div className="dialog-actions">
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button disabled={!canSubmit} type="submit">{editing ? 'Save source' : 'Register source'}</Button>
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
