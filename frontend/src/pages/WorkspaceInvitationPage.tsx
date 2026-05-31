import { Link2, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useData } from '../data/useData'
import './WorkspaceInvitationPage.css'

type AcceptState = 'idle' | 'accepting' | 'accepted' | 'failed'

export function WorkspaceInvitationPage() {
  const { invitationId } = useParams()
  const navigate = useNavigate()
  const { acceptWorkspaceInvitation } = useData()
  const [acceptState, setAcceptState] = useState<AcceptState>('idle')

  async function acceptInvitation() {
    if (!invitationId) {
      setAcceptState('failed')
      return
    }

    setAcceptState('accepting')
    const accepted = await acceptWorkspaceInvitation(invitationId)
    setAcceptState(accepted ? 'accepted' : 'failed')

    if (accepted) {
      navigate('/dashboard')
    }
  }

  return (
    <section className="workspace-invitation-page panel">
      <Link2 aria-hidden="true" size={22} />
      <p className="eyebrow">Workspace invite link</p>
      <h2>Accept Workspace invitation</h2>
      <p>
        This link grants the Workspace groups selected by an admin only after a signed-in account accepts it.
      </p>
      <div className="workspace-invitation-actions">
        <button disabled={acceptState === 'accepting' || acceptState === 'accepted'} onClick={() => void acceptInvitation()} type="button">
          <ShieldCheck aria-hidden="true" size={16} />
          {acceptState === 'accepting' ? 'Accepting...' : 'Accept invitation'}
        </button>
        <Link to="/dashboard">Back to dashboard</Link>
      </div>
      {acceptState === 'failed' ? <p className="workspace-invitation-status">This invitation link is unavailable, expired, already accepted, or already belongs to an active member.</p> : null}
    </section>
  )
}
