import { ArrowLeft, Crown, Link2, ShieldCheck, UserRound, UsersRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useData } from '../data/useData'
import type { WorkspaceGroup, WorkspaceInvitation, WorkspaceMembership } from '../types'
import './WorkspaceInvitationPage.css'

type AcceptState = 'idle' | 'accepting' | 'accepted' | 'failed'

export function WorkspaceInvitationPage() {
  const { invitationId } = useParams()
  const navigate = useNavigate()
  const { acceptWorkspaceInvitation, workspaceAdmin, workspaceDirectory } = useData()
  const [acceptState, setAcceptState] = useState<AcceptState>('idle')
  const invitation = findInvitation(invitationId, workspaceDirectory.pendingInvitations, workspaceAdmin.invitations)
  const workspace = invitation
    ? workspaceDirectory.workspaces.find((item) => item.workspaceId === invitation.workspaceId)
      ?? (workspaceAdmin.workspace?.workspaceId === invitation.workspaceId ? workspaceAdmin.workspace : null)
    : null
  const owner = invitation ? findWorkspaceOwner(invitation.workspaceId, workspaceAdmin.members) : null
  const groupNames = invitation ? invitation.groupIds.map((groupId) => groupLabel(groupId, workspaceAdmin.groups)) : []
  const workspaceName = workspace?.name ?? 'Workspace invitation'
  const memberCount = workspace?.memberCount ?? activeMemberCount(invitation?.workspaceId, workspaceAdmin.members)

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
      <p className="eyebrow">Workspace invitation</p>
      <h2>Join {workspaceName}</h2>
      {workspace?.description ? <p className="workspace-invitation-intro">{workspace.description}</p> : null}
      <dl className="workspace-invitation-summary" aria-label="Invitation details">
        <div>
          <dt><Crown aria-hidden="true" size={15} />Owner</dt>
          <dd>{owner?.displayName ?? invitation?.invitedByDisplayName ?? 'Unknown'}</dd>
        </div>
        <div>
          <dt><UsersRound aria-hidden="true" size={15} />Members</dt>
          <dd>{memberCount ?? 'Unknown'}</dd>
        </div>
        <div>
          <dt><UserRound aria-hidden="true" size={15} />Group</dt>
          <dd>{groupNames.length > 0 ? groupNames.join(', ') : 'Pending invite'}</dd>
        </div>
      </dl>
      <div className="workspace-invitation-actions">
        <button disabled={acceptState === 'accepting' || acceptState === 'accepted'} onClick={() => void acceptInvitation()} type="button">
          <ShieldCheck aria-hidden="true" size={16} />
          {acceptState === 'accepting' ? 'Accepting...' : 'Accept invitation'}
        </button>
        <Link to="/dashboard"><ArrowLeft aria-hidden="true" size={16} />Back</Link>
      </div>
      {acceptState === 'failed' ? <p className="workspace-invitation-status">This invitation link is unavailable, expired, already accepted, or already belongs to an active member.</p> : null}
    </section>
  )
}

function findInvitation(invitationId: string | undefined, pending: WorkspaceInvitation[], adminInvitations: WorkspaceInvitation[]) {
  if (!invitationId) {
    return null
  }

  return pending.find((item) => item.invitationId === invitationId)
    ?? adminInvitations.find((item) => item.invitationId === invitationId)
    ?? null
}

function findWorkspaceOwner(workspaceId: string, members: WorkspaceMembership[]) {
  return members.find((member) => (
    member.workspaceId === workspaceId
    && member.status === 'active'
    && member.groupIds.includes('workspace_owner')
  )) ?? null
}

function activeMemberCount(workspaceId: string | undefined, members: WorkspaceMembership[]) {
  if (!workspaceId) {
    return null
  }

  return members.filter((member) => member.workspaceId === workspaceId && member.status === 'active').length
}

function groupLabel(groupId: string, groups: WorkspaceGroup[]) {
  return groups.find((group) => group.groupId === groupId)?.name ?? groupId
}
