import { AlertCircle, ArrowRight, BarChart3, Check, Copy, KeyRound, Link2, Save, Settings2, ShieldCheck, Trash2, UsersRound } from 'lucide-react'
import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../data/useData'
import type { Workspace, WorkspaceChartDatum, WorkspaceGroup, WorkspaceInvitation, WorkspaceMembership } from '../types'
import './WorkspaceAdminPage.css'

export function WorkspaceAdminPage() {
  const {
    createWorkspaceInvitation,
    deleteWorkspace,
    metrics,
    transferWorkspaceOwner,
    workspaceAdmin,
    workspaceDirectory,
  } = useData()
  const [generatedInvitation, setGeneratedInvitation] = useState<WorkspaceInvitation | null>(null)
  const [copiedInvitationId, setCopiedInvitationId] = useState('')
  const [ownerTransferEmail, setOwnerTransferEmail] = useState('')
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [selectedGroups, setSelectedGroups] = useState<string[]>(() => {
    const defaultGroup = workspaceAdmin.groups.find((group) => group.groupId === 'privacy_reviewer') ?? workspaceAdmin.groups[0]
    return defaultGroup ? [defaultGroup.groupId] : []
  })
  const canInvite = workspaceAdmin.permissionBoundary.allowedActions.includes('invite_workspace_members')
  const canManageOwnership = workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_ownership')
  const canManageSettings = workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_settings')
  const workspace = workspaceAdmin.workspace
  const memberCount = workspace?.memberCount ?? workspaceAdmin.members.length
  const openBacklog = metrics.openReviewBacklog ?? 0
  const highRisk = metrics.highRiskFindings ?? 0
  const defaultGroup = workspaceAdmin.groups.find((group) => group.groupId === 'privacy_reviewer') ?? workspaceAdmin.groups[0]
  const invitableGroups = workspaceAdmin.groups.filter((group) => group.groupId !== 'workspace_owner')
  const previewMembers = workspaceAdmin.members.slice(0, 4)
  const remainingMemberCount = Math.max(0, workspaceAdmin.members.length - previewMembers.length)
  const previewGroups = workspaceAdmin.groups.slice(0, 4)
  const remainingGroupCount = Math.max(0, workspaceAdmin.groups.length - previewGroups.length)
  const totalGroupPermissions = workspaceAdmin.groups.reduce((total, group) => total + group.permissions.length, 0)
  const availableGroupIds = new Set(invitableGroups.map((group) => group.groupId))
  const selectedGroupIds = (selectedGroups.length > 0 ? selectedGroups : (defaultGroup ? [defaultGroup.groupId] : []))
    .filter((groupId) => availableGroupIds.has(groupId))
  const currentAccountId = workspaceAdmin.currentMembership?.accountId
  const ownerTransferTargets = workspaceAdmin.members.filter((member) => member.status === 'active' && member.accountId !== currentAccountId)
  const ownerTransferEmailValue = ownerTransferEmail.trim().toLowerCase()
  const ownerTransferTarget = ownerTransferEmailValue
    ? ownerTransferTargets.find((member) => member.email?.trim().toLowerCase() === ownerTransferEmailValue)
    : undefined
  const ownerTransferEmailMismatch = Boolean(ownerTransferEmail.trim()) && !ownerTransferTarget

  function toggleGroup(groupId: string) {
    setSelectedGroups((current) => {
      const active = current.length > 0 ? current : selectedGroupIds
      return (
        active.includes(groupId)
          ? active.filter((item) => item !== groupId)
          : [...active, groupId]
      )
    })
  }

  async function submitInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!workspace || selectedGroupIds.length === 0) {
      return
    }

    const invitation = await createWorkspaceInvitation({
      workspaceId: workspace.workspaceId,
      groupIds: selectedGroupIds,
    })

    if (invitation) {
      setGeneratedInvitation(invitation)
      setCopiedInvitationId('')
    }
  }

  async function copyInvitationLink(invitation: WorkspaceInvitation) {
    if (!navigator.clipboard) {
      return
    }

    await navigator.clipboard.writeText(invitationLink(invitation))
    setCopiedInvitationId(invitation.invitationId)
  }

  async function submitOwnerTransfer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!workspace || !ownerTransferTarget) {
      return
    }

    if (!window.confirm(`Transfer Workspace owner to ${memberLabel(ownerTransferTarget)}?`)) {
      return
    }

    const transferred = await transferWorkspaceOwner({
      workspaceId: workspace.workspaceId,
      membershipId: ownerTransferTarget.membershipId,
    })

    if (transferred) {
      setOwnerTransferEmail('')
    }
  }

  async function submitWorkspaceDelete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!workspace || deleteConfirmation !== workspace.name) {
      return
    }

    if (!window.confirm(`Delete Workspace "${workspace.name}"? This removes Workspace memberships and pending invites, but does not delete external source files.`)) {
      return
    }

    const deleted = await deleteWorkspace({
      workspaceId: workspace.workspaceId,
      workspaceName: deleteConfirmation,
    })

    if (deleted) {
      setDeleteConfirmation('')
    }
  }

  if (!workspaceDirectory.currentWorkspaceId && workspaceDirectory.workspaceRequired) {
    return (
      <section className="workspace-admin-empty panel">
        <AlertCircle aria-hidden="true" size={22} />
        <p className="eyebrow">Workspace required</p>
        <h2>No Workspace membership yet</h2>
        <p>
          This account can sign in, but it cannot enter DataSentinel operations until it opens and accepts a Workspace invite link.
        </p>
        <PendingInvitations />
      </section>
    )
  }

  if (!workspace || !workspaceAdmin.permissionBoundary.allowedActions.includes('view_workspace_admin')) {
    return (
      <section className="workspace-admin-empty panel">
        <ShieldCheck aria-hidden="true" size={22} />
        <p className="eyebrow">Permission boundary</p>
        <h2>Workspace admin access denied</h2>
        <p>Your current Workspace groups do not include administrator permissions.</p>
        <DeniedActions />
      </section>
    )
  }

  return (
    <div className="workspace-admin-page">
      <section className="workspace-admin-hero">
        <div>
          <p className="eyebrow">Workspace admin</p>
          <h2>{workspace.name}</h2>
          {workspace.description ? <p>{workspace.description}</p> : null}
        </div>
        <div className="workspace-admin-kpis" aria-label="Workspace overview">
          <MetricTile label="Members" value={memberCount} />
          <MetricTile label="Pending invites" value={workspace.pendingInvitationCount} />
          <MetricTile label="Open backlog" value={openBacklog} />
          <MetricTile label="High risk" value={highRisk} />
        </div>
      </section>

      <div className="workspace-admin-grid">
        <section className="panel workspace-admin-invite" aria-labelledby="workspace-invite-title">
          <div className="workspace-section-heading">
            <Link2 aria-hidden="true" size={18} />
            <div>
              <h3 id="workspace-invite-title">Invite link</h3>
            </div>
          </div>
          <form onSubmit={submitInvitation}>
            <fieldset disabled={!canInvite}>
              <legend>Groups granted by this link</legend>
              <div className="workspace-group-picks">
                {invitableGroups.map((group) => (
                  <label key={group.groupId}>
                    <input
                      checked={selectedGroupIds.includes(group.groupId)}
                      onChange={() => toggleGroup(group.groupId)}
                      type="checkbox"
                    />
                    <span>{group.name}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <button disabled={!canInvite || selectedGroupIds.length === 0} type="submit">
              <Link2 aria-hidden="true" size={16} />
              Generate invite link
            </button>
          </form>
          {generatedInvitation ? (
            <div className="workspace-invite-link-card" aria-live="polite">
              <span>
                <strong>Invite link ready</strong>
                <small>{generatedInvitation.groupIds.map((groupId) => groupLabel(groupId, workspaceAdmin.groups)).join(', ')}</small>
              </span>
              <a href={invitationLink(generatedInvitation)}>{invitationLink(generatedInvitation)}</a>
              <button onClick={() => void copyInvitationLink(generatedInvitation)} type="button">
                {copiedInvitationId === generatedInvitation.invitationId ? <Check aria-hidden="true" size={15} /> : <Copy aria-hidden="true" size={15} />}
                {copiedInvitationId === generatedInvitation.invitationId ? 'Copied' : 'Copy link'}
              </button>
            </div>
          ) : null}
          <DeniedActions />
        </section>

        <section className="panel workspace-admin-charts" aria-labelledby="workspace-charts-title">
          <div className="workspace-section-heading">
            <BarChart3 aria-hidden="true" size={18} />
            <div>
              <h3 id="workspace-charts-title">Workspace charts</h3>
            </div>
          </div>
          <ChartGroup title="Members by group" data={workspaceAdmin.charts.membersByGroup} />
          <ChartGroup title="Review load" data={workspaceAdmin.charts.reviewLoad} />
          <ChartGroup title="Scan coverage" data={workspaceAdmin.charts.scanCoverage} />
        </section>
      </div>

      <div className="workspace-admin-grid workspace-admin-grid-wide">
        <section className="panel workspace-admin-list" aria-labelledby="workspace-members-title">
          <div className="workspace-section-heading">
            <UsersRound aria-hidden="true" size={18} />
            <div>
              <h3 id="workspace-members-title">Members</h3>
            </div>
            <Link className="workspace-section-link" to="/workspace/admin/members">
              Members page
              <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </div>
          <div className="workspace-member-list">
            {previewMembers.map((member) => (
              <article className="workspace-member-row" key={member.membershipId}>
                <span className="workspace-member-avatar" aria-hidden="true">{initials(member.displayName)}</span>
                <span>
                  <strong>{member.displayName}</strong>
                  <small>{member.email ?? member.accountId}</small>
                </span>
                <span className="workspace-role-stack">
                  {member.groupIds.length > 0
                    ? member.groupIds.map((groupId) => <small key={groupId}>{groupLabel(groupId, workspaceAdmin.groups)}</small>)
                    : <small>No groups</small>}
                </span>
              </article>
            ))}
            {remainingMemberCount > 0 ? (
              <Link className="workspace-summary-more" to="/workspace/admin/members">
                View {remainingMemberCount} more member{remainingMemberCount === 1 ? '' : 's'}
                <ArrowRight aria-hidden="true" size={15} />
              </Link>
            ) : null}
          </div>
        </section>

        <section className="panel workspace-admin-list" aria-labelledby="workspace-groups-title">
          <div className="workspace-section-heading">
            <ShieldCheck aria-hidden="true" size={18} />
            <div>
              <h3 id="workspace-groups-title">Group controls</h3>
            </div>
            <Link className="workspace-section-link" to="/workspace/admin/groups">
              Group controls
              <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </div>
          <div className="workspace-group-overview" aria-label="Group controls summary">
            <SummaryPill label="Groups" value={workspaceAdmin.groups.length} />
            <SummaryPill label="Permission grants" value={totalGroupPermissions} />
            <SummaryPill label="Invitable groups" value={invitableGroups.length} />
          </div>
          <div className="workspace-group-list">
            {previewGroups.map((group) => (
              <article className="workspace-group-row" key={group.groupId}>
                <div className="workspace-group-summary workspace-group-summary-compact">
                  <span className="workspace-group-summary-copy">
                    <strong>{group.name}</strong>
                  </span>
                  <span className="workspace-group-summary-meta">
                    <small>{group.memberCount} members</small>
                    <small>{group.permissions.length} permissions</small>
                  </span>
                </div>
              </article>
            ))}
            {remainingGroupCount > 0 ? (
              <Link className="workspace-summary-more" to="/workspace/admin/groups">
                View {remainingGroupCount} more group{remainingGroupCount === 1 ? '' : 's'}
                <ArrowRight aria-hidden="true" size={15} />
              </Link>
            ) : null}
          </div>
        </section>
      </div>

      <section className="panel workspace-admin-list" aria-labelledby="workspace-invitations-title">
        <div className="workspace-section-heading">
          <Link2 aria-hidden="true" size={18} />
            <div>
              <h3 id="workspace-invitations-title">Invitations</h3>
            </div>
          </div>
        <div className="workspace-invitation-list">
          {workspaceAdmin.invitations.map((invitation) => (
            <article className={`workspace-invitation-row workspace-invitation-row-${invitation.status}`} key={invitation.invitationId}>
              <span className="workspace-invitation-main">
                <a href={invitationLink(invitation)}>{invitationLink(invitation)}</a>
                <small>
                  {groupListLabel(invitation.groupIds, workspaceAdmin.groups)}
                  <span aria-hidden="true"> · </span>
                  <time dateTime={invitation.expiresAt}>Expires {formatDate(invitation.expiresAt)}</time>
                </small>
              </span>
              <span className={`workspace-invitation-status workspace-invitation-status-${invitation.status}`}>{invitation.status}</span>
              {invitation.status === 'pending' ? (
                <button onClick={() => void copyInvitationLink(invitation)} type="button">
                  {copiedInvitationId === invitation.invitationId ? <Check aria-hidden="true" size={15} /> : <Copy aria-hidden="true" size={15} />}
                  {copiedInvitationId === invitation.invitationId ? 'Copied' : 'Copy'}
                </button>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <WorkspaceProfileSettings
        canManageSettings={canManageSettings}
        key={workspace.workspaceId}
        workspace={workspace}
      />

      <section className="panel workspace-danger-zone" aria-labelledby="workspace-danger-title">
        <div className="workspace-section-heading">
          <Trash2 aria-hidden="true" size={18} />
          <div>
            <h3 id="workspace-danger-title">Danger Zone</h3>
          </div>
        </div>
        <div className="workspace-danger-grid">
          <form className="workspace-danger-card" onSubmit={(event) => void submitOwnerTransfer(event)}>
            <span>
              <KeyRound aria-hidden="true" size={17} />
              <strong>Transfer owner</strong>
            </span>
            <label>
              <span>New owner email</span>
              <input
                disabled={!canManageOwnership || ownerTransferTargets.length === 0}
                onChange={(event) => setOwnerTransferEmail(event.target.value)}
                placeholder="member@example.com"
                type="email"
                value={ownerTransferEmail}
              />
            </label>
            {ownerTransferTarget ? (
              <small className="workspace-danger-match">Matched {memberLabel(ownerTransferTarget)}</small>
            ) : null}
            {ownerTransferEmailMismatch ? (
              <small className="workspace-danger-warning">No active Workspace member matches this email.</small>
            ) : null}
            <button disabled={!canManageOwnership || !ownerTransferTarget} type="submit">
              <KeyRound aria-hidden="true" size={15} />
              Transfer owner
            </button>
          </form>

          <form className="workspace-danger-card workspace-danger-delete" onSubmit={(event) => void submitWorkspaceDelete(event)}>
            <span>
              <Trash2 aria-hidden="true" size={17} />
              <strong>Delete Workspace</strong>
            </span>
            <small className="workspace-danger-warning">External source files are not deleted.</small>
            <label>
              <span>Type {workspace.name} to confirm</span>
              <input
                disabled={!canManageOwnership}
                onChange={(event) => setDeleteConfirmation(event.target.value)}
                placeholder={workspace.name}
                value={deleteConfirmation}
              />
            </label>
            <button disabled={!canManageOwnership || deleteConfirmation !== workspace.name} type="submit">
              <Trash2 aria-hidden="true" size={15} />
              Delete Workspace
            </button>
          </form>
        </div>
      </section>
    </div>
  )
}

function WorkspaceProfileSettings({
  canManageSettings,
  workspace,
}: {
  canManageSettings: boolean
  workspace: Workspace
}) {
  const { updateWorkspaceSettings } = useData()
  const [workspaceName, setWorkspaceName] = useState(workspace.name)
  const [workspaceDescription, setWorkspaceDescription] = useState(workspace.description ?? '')
  const normalizedWorkspaceName = workspaceName.trim().replace(/\s+/g, ' ')
  const normalizedWorkspaceDescription = workspaceDescription.trim().replace(/\s+/g, ' ')
  const workspaceProfileChanged = (
    normalizedWorkspaceName !== workspace.name
    || normalizedWorkspaceDescription !== (workspace.description ?? '')
  )

  async function submitWorkspaceSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const updated = await updateWorkspaceSettings({
      workspaceId: workspace.workspaceId,
      description: normalizedWorkspaceDescription,
      name: normalizedWorkspaceName,
    })

    if (updated) {
      setWorkspaceName(normalizedWorkspaceName)
      setWorkspaceDescription(normalizedWorkspaceDescription)
    }
  }

  return (
    <section className="panel workspace-profile-settings" aria-labelledby="workspace-profile-title">
      <div className="workspace-section-heading">
        <Settings2 aria-hidden="true" size={18} />
        <div>
          <h3 id="workspace-profile-title">Workspace profile</h3>
        </div>
      </div>
      <form onSubmit={(event) => void submitWorkspaceSettings(event)}>
        <fieldset disabled={!canManageSettings}>
          <label>
            <span>Workspace name</span>
            <input
              maxLength={80}
              onChange={(event) => setWorkspaceName(event.target.value)}
              placeholder="DataSentinel GDPR"
              value={workspaceName}
            />
          </label>
          <label>
            <span>Introduction</span>
            <textarea
              maxLength={240}
              onChange={(event) => setWorkspaceDescription(event.target.value)}
              placeholder="Privacy operations workspace"
              rows={3}
              value={workspaceDescription}
            />
          </label>
        </fieldset>
        <div className="workspace-profile-preview" aria-label="Workspace profile preview">
          <span className="workspace-profile-avatar" aria-hidden="true">{initials(normalizedWorkspaceName)}</span>
          <span>
            <strong>{normalizedWorkspaceName || workspace.name}</strong>
            <small>{normalizedWorkspaceDescription || 'No introduction shown'}</small>
          </span>
        </div>
        <button
          disabled={!canManageSettings || !normalizedWorkspaceName || !workspaceProfileChanged}
          type="submit"
        >
          <Save aria-hidden="true" size={15} />
          Save profile
        </button>
      </form>
    </section>
  )
}

function MetricTile({ label, value }: { label: string; value: number }) {
  return (
    <span>
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
  )
}

function SummaryPill({ label, value }: { label: string; value: number }) {
  return (
    <span>
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
  )
}

function ChartGroup({ data, title }: { data: WorkspaceChartDatum[]; title: string }) {
  const max = useMemo(() => Math.max(1, ...data.map((item) => item.value)), [data])

  return (
    <div className="workspace-chart-group">
      <h4>{title}</h4>
      {data.length === 0 ? <p>No chart data available.</p> : null}
      {data.map((item) => (
        <div className="workspace-chart-row" key={`${title}-${item.label}`}>
          <span>{item.label}</span>
          <div aria-hidden="true">
            <span className={`workspace-chart-bar workspace-chart-${item.tone ?? 'neutral'}`} style={{ width: `${Math.max(6, (item.value / max) * 100)}%` }} />
          </div>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  )
}

function DeniedActions() {
  const { workspaceAdmin } = useData()
  const relevantDenials = workspaceAdmin.permissionBoundary.deniedActions.filter((item) => (
    item.action.includes('workspace') || item.action.includes('deletion') || item.action.includes('directory')
  ))

  if (relevantDenials.length === 0) {
    return null
  }

  return (
    <div className="workspace-denied-actions">
      {relevantDenials.map((item) => (
        <p key={item.action}><strong>{item.action}</strong> {item.reason}</p>
      ))}
    </div>
  )
}

function PendingInvitations() {
  const { acceptWorkspaceInvitation, workspaceDirectory } = useData()

  if (workspaceDirectory.pendingInvitations.length === 0) {
    return <p className="workspace-no-invite">No invite link is open in this session.</p>
  }

  return (
    <div className="workspace-pending-invites">
      {workspaceDirectory.pendingInvitations.map((invitation) => (
        <article key={invitation.invitationId}>
          <span>
            <strong>{invitationLink(invitation)}</strong>
            <small>{invitation.groupIds.join(', ')}</small>
          </span>
          <button onClick={() => void acceptWorkspaceInvitation(invitation.invitationId)} type="button">Accept</button>
        </article>
      ))}
    </div>
  )
}

function groupLabel(groupId: string, groups: WorkspaceGroup[]) {
  return groups.find((group) => group.groupId === groupId)?.name ?? groupId
}

function groupListLabel(groupIds: string[], groups: WorkspaceGroup[]) {
  return groupIds.length > 0 ? groupIds.map((groupId) => groupLabel(groupId, groups)).join(', ') : 'No groups'
}

function memberLabel(member: WorkspaceMembership) {
  return member.email ? `${member.displayName} (${member.email})` : member.displayName
}

function initials(value: string) {
  const letters = value.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('')
  return letters || 'WS'
}

function formatDate(value: string) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(parsed)
}

function invitationLink(invitation: WorkspaceInvitation) {
  const path = invitation.invitePath || `/workspace/invitations/${invitation.invitationId}`
  return new URL(path, window.location.origin).toString()
}
