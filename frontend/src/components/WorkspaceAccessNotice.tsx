import { AlertCircle, Link2 } from 'lucide-react'
import { useState } from 'react'
import { useData } from '../data/useData'
import { WorkspaceCreateForm } from './WorkspaceCreateForm'
import './WorkspaceAccessNotice.css'

export function WorkspaceAccessNotice() {
  const { acceptWorkspaceInvitation, workspaceDirectory } = useData()
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <section className="workspace-access-notice panel">
      <AlertCircle aria-hidden="true" size={22} />
      <p className="eyebrow">Workspace required</p>
      <h2>No Workspace membership yet</h2>
      <p>
        This account is signed in, but lawdit operations require Workspace membership. Create a Workspace to become its admin, or open an invite link from an existing Workspace admin.
      </p>
      <button className="workspace-access-create" onClick={() => setCreateOpen(true)} type="button">
        Create Workspace
      </button>
      <WorkspaceCreateForm onClose={() => setCreateOpen(false)} open={createOpen} />
      {workspaceDirectory.pendingInvitations.length > 0 ? (
        <div className="workspace-access-invitations">
          {workspaceDirectory.pendingInvitations.map((invitation) => (
            <article key={invitation.invitationId}>
              <span>
                <strong>{invitation.invitePath ?? invitation.invitationId}</strong>
                <small>{invitation.groupIds.join(', ')}</small>
              </span>
              <button onClick={() => void acceptWorkspaceInvitation(invitation.invitationId)} type="button">
                <Link2 aria-hidden="true" size={16} />
                Accept invitation
              </button>
            </article>
          ))}
        </div>
      ) : (
        <p className="workspace-access-empty">No invite link is open in this session.</p>
      )}
    </section>
  )
}
