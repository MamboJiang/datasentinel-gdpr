import { ShieldCheck, UsersRound, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { useData } from '../data/useData'
import { useI18n } from '../i18n'
import './WorkspaceCreateForm.css'

export function WorkspaceCreateForm({ onClose, open }: { onClose: () => void; open: boolean }) {
  const { createWorkspace } = useData()
  const { t } = useI18n()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  useEffect(() => {
    if (!open) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose, open])

  if (!open) {
    return null
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = name.trim()

    if (!trimmed) {
      return
    }

    createWorkspace({ description: description.trim() || undefined, name: trimmed })
    setName('')
    setDescription('')
    onClose()
  }

  return (
    <div className="workspace-create-modal" role="presentation">
      <button className="workspace-create-modal-backdrop" onClick={onClose} type="button" aria-label={t('Close create Workspace dialog')} />
      <section aria-labelledby="workspace-create-title" aria-modal="true" className="workspace-create-dialog" role="dialog">
        <header>
          <div>
            <p className="eyebrow">{t('New Workspace')}</p>
            <h2 id="workspace-create-title">{t('Create Workspace')}</h2>
          </div>
          <button className="workspace-create-close" onClick={onClose} type="button" aria-label={t('Close create Workspace dialog')}>
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        <form className="workspace-create-form" onSubmit={submit}>
          <label>
            <span>{t('Workspace name')}</span>
            <input
              autoFocus
              onChange={(event) => setName(event.target.value)}
              placeholder={t('Privacy Operations')}
              type="text"
              value={name}
            />
          </label>
          <label>
            <span>{t('Description')}</span>
            <textarea
              onChange={(event) => setDescription(event.target.value)}
              placeholder={t('Workspace for privacy review, source scanning, and audit evidence.')}
              rows={3}
              value={description}
            />
          </label>

          <div className="workspace-create-settings" aria-label={t('Workspace settings')}>
            <article>
              <ShieldCheck aria-hidden="true" size={17} />
              <span>
                <strong>{t('Creator role')}</strong>
                <small>{t('You will be added to Workspace admins automatically.')}</small>
              </span>
            </article>
            <article>
              <UsersRound aria-hidden="true" size={17} />
              <span>
                <strong>{t('Default groups')}</strong>
                <small>{t('Admins, privacy reviewers, data stewards, and auditors are created for this Workspace.')}</small>
              </span>
            </article>
          </div>

          <footer>
            <button className="workspace-create-secondary" onClick={onClose} type="button">{t('Cancel')}</button>
            <button className="workspace-create-primary" disabled={!name.trim()} type="submit">{t('Create Workspace')}</button>
          </footer>
        </form>
      </section>
    </div>
  )
}
