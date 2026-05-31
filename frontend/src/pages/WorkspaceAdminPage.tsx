import { AlertCircle, ArrowRight, BarChart3, Check, Copy, Link2, Pencil, Plus, Save, ShieldCheck, Trash2, UsersRound, X } from 'lucide-react'
import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../data/useData'
import type { WorkspaceChartDatum, WorkspaceGroup, WorkspaceInvitation, WorkspacePermissionOption } from '../types'
import './WorkspaceAdminPage.css'

type GroupDraft = {
  description: string
  name: string
  permissions: string[]
}

export function WorkspaceAdminPage() {
  const {
    createWorkspaceGroup,
    createWorkspaceInvitation,
    deleteWorkspaceGroup,
    metrics,
    updateWorkspaceGroup,
    workspaceAdmin,
    workspaceDirectory,
  } = useData()
  const [generatedInvitation, setGeneratedInvitation] = useState<WorkspaceInvitation | null>(null)
  const [copiedInvitationId, setCopiedInvitationId] = useState('')
  const [createGroupOpen, setCreateGroupOpen] = useState(false)
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null)
  const [groupDrafts, setGroupDrafts] = useState<Record<string, GroupDraft>>({})
  const [newGroupDescription, setNewGroupDescription] = useState('')
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupPermissions, setNewGroupPermissions] = useState<string[]>(['view_assigned_findings'])
  const [selectedGroups, setSelectedGroups] = useState<string[]>(() => {
    const defaultGroup = workspaceAdmin.groups.find((group) => group.groupId === 'privacy_reviewer') ?? workspaceAdmin.groups[0]
    return defaultGroup ? [defaultGroup.groupId] : []
  })
  const canInvite = workspaceAdmin.permissionBoundary.allowedActions.includes('invite_workspace_members')
  const canManageGroups = workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_groups')
  const workspace = workspaceAdmin.workspace
  const memberCount = workspace?.memberCount ?? workspaceAdmin.members.length
  const openBacklog = metrics.openReviewBacklog ?? 0
  const highRisk = metrics.highRiskFindings ?? 0
  const defaultGroup = workspaceAdmin.groups.find((group) => group.groupId === 'privacy_reviewer') ?? workspaceAdmin.groups[0]
  const availableGroupIds = new Set(workspaceAdmin.groups.map((group) => group.groupId))
  const selectedGroupIds = (selectedGroups.length > 0 ? selectedGroups : (defaultGroup ? [defaultGroup.groupId] : []))
    .filter((groupId) => availableGroupIds.has(groupId))
  const availablePermissions = workspaceAdmin.availablePermissions

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

  function draftForGroup(group: WorkspaceGroup): GroupDraft {
    return groupDrafts[group.groupId] ?? {
      description: group.description ?? '',
      name: group.name,
      permissions: group.permissions,
    }
  }

  function updateGroupDraft(group: WorkspaceGroup, patch: Partial<GroupDraft>) {
    setGroupDrafts((current) => ({
      ...current,
      [group.groupId]: {
        ...(current[group.groupId] ?? {
          description: group.description ?? '',
          name: group.name,
          permissions: group.permissions,
        }),
        ...patch,
      },
    }))
  }

  function toggleDraftPermission(group: WorkspaceGroup, permission: string) {
    const draft = draftForGroup(group)
    updateGroupDraft(group, {
      permissions: draft.permissions.includes(permission)
        ? draft.permissions.filter((item) => item !== permission)
        : [...draft.permissions, permission],
    })
  }

  function toggleNewGroupPermission(permission: string) {
    setNewGroupPermissions((current) => (
      current.includes(permission)
        ? current.filter((item) => item !== permission)
        : [...current, permission]
    ))
  }

  async function submitNewGroup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!workspace || !newGroupName.trim()) {
      return
    }

    const group = await createWorkspaceGroup({
      workspaceId: workspace.workspaceId,
      name: newGroupName.trim(),
      description: newGroupDescription.trim(),
      permissions: newGroupPermissions,
    })

    if (group) {
      setNewGroupName('')
      setNewGroupDescription('')
      setNewGroupPermissions(['view_assigned_findings'])
      setCreateGroupOpen(false)
    }
  }

  async function submitGroupUpdate(event: FormEvent<HTMLFormElement>, group: WorkspaceGroup) {
    event.preventDefault()

    if (!workspace) {
      return
    }

    const draft = draftForGroup(group)
    const updated = await updateWorkspaceGroup({
      workspaceId: workspace.workspaceId,
      groupId: group.groupId,
      name: draft.name.trim(),
      description: draft.description.trim(),
      permissions: draft.permissions,
    })

    if (updated) {
      setGroupDrafts((current) => {
        const remaining = { ...current }
        delete remaining[group.groupId]
        return remaining
      })
      setEditingGroupId(null)
    }
  }

  async function removeGroup(group: WorkspaceGroup) {
    if (!workspace) {
      return
    }

    const deleted = await deleteWorkspaceGroup({
      workspaceId: workspace.workspaceId,
      groupId: group.groupId,
    })

    if (deleted) {
      setSelectedGroups((current) => current.filter((groupId) => groupId !== group.groupId))
      setGroupDrafts((current) => {
        const remaining = { ...current }
        delete remaining[group.groupId]
        return remaining
      })
      setEditingGroupId((current) => current === group.groupId ? null : current)
    }
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
          <p>{workspace.description ?? 'Workspace-scoped administration, invitations, groups, and management evidence.'}</p>
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
              <p>Generate a link that creates Workspace membership only after a signed-in account opens and accepts it.</p>
            </div>
          </div>
          <form onSubmit={submitInvitation}>
            <fieldset disabled={!canInvite}>
              <legend>Groups granted by this link</legend>
              <div className="workspace-group-picks">
                {workspaceAdmin.groups.map((group) => (
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
              <p>Operational overview from Workspace state and existing admin metrics.</p>
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
              <p>Membership is Workspace-scoped; account sign-in alone grants no Workspace access.</p>
            </div>
            <Link className="workspace-section-link" to="/workspace/admin/members">
              Members page
              <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </div>
          <div className="workspace-member-list">
            {workspaceAdmin.members.map((member) => (
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
          </div>
        </section>

        <section className="panel workspace-admin-list workspace-group-manager" aria-labelledby="workspace-groups-title">
          <div className="workspace-section-heading">
            <ShieldCheck aria-hidden="true" size={18} />
            <div>
              <h3 id="workspace-groups-title">Group controls</h3>
              <p>Permissions are explicit, scoped to this Workspace, and denied by default.</p>
            </div>
          </div>
          {createGroupOpen ? (
            <form className="workspace-group-create" id="workspace-group-create-panel" onSubmit={submitNewGroup}>
              <div className="workspace-group-create-header">
                <strong>New group</strong>
                <button
                  aria-label="Close new group form"
                  className="workspace-group-icon-button"
                  onClick={() => setCreateGroupOpen(false)}
                  type="button"
                >
                  <X aria-hidden="true" size={15} />
                </button>
              </div>
              <fieldset disabled={!canManageGroups}>
                <label>
                  <span>Group name</span>
                  <input
                    onChange={(event) => setNewGroupName(event.target.value)}
                    placeholder="Legal reviewers"
                    value={newGroupName}
                  />
                </label>
                <label>
                  <span>Description</span>
                  <textarea
                    onChange={(event) => setNewGroupDescription(event.target.value)}
                    placeholder="Review legal escalation evidence."
                    rows={2}
                    value={newGroupDescription}
                  />
                </label>
                <PermissionGrid
                  disabled={!canManageGroups}
                  onToggle={toggleNewGroupPermission}
                  options={availablePermissions}
                  selected={newGroupPermissions}
                />
              </fieldset>
              <button disabled={!canManageGroups || !newGroupName.trim()} type="submit">
                <Plus aria-hidden="true" size={16} />
                Add group
              </button>
            </form>
          ) : (
            <button
              aria-controls="workspace-group-create-panel"
              aria-expanded={createGroupOpen}
              className="workspace-group-create-toggle"
              disabled={!canManageGroups}
              onClick={() => setCreateGroupOpen(true)}
              type="button"
            >
              <Plus aria-hidden="true" size={16} />
              New group
            </button>
          )}
          <div className="workspace-group-list">
            {workspaceAdmin.groups.map((group) => {
              const draft = draftForGroup(group)
              const editing = editingGroupId === group.groupId
              const lockedAdminDelete = group.groupId === 'workspace_admin'
              return (
                <article className={`workspace-group-row ${editing ? 'workspace-group-row-open' : ''}`} key={group.groupId}>
                  <div className="workspace-group-summary">
                    <span className="workspace-group-summary-copy">
                      <strong>{group.name}</strong>
                      <small>{group.description || 'No description'}</small>
                    </span>
                    <span className="workspace-group-summary-meta">
                      <small>{group.memberCount} members</small>
                      <small>{group.permissions.length} permissions</small>
                    </span>
                    <button
                      aria-controls={`workspace-group-editor-${group.groupId}`}
                      aria-expanded={editing}
                      aria-label={`Edit ${group.name}`}
                      className="workspace-group-icon-button"
                      disabled={!canManageGroups}
                      onClick={() => setEditingGroupId(editing ? null : group.groupId)}
                      type="button"
                    >
                      <Pencil aria-hidden="true" size={15} />
                    </button>
                  </div>
                  <div className="workspace-group-permissions-preview" aria-label={`${group.name} permission preview`}>
                    {group.permissions.slice(0, 3).map((permission) => <small key={permission}>{permissionLabel(permission, availablePermissions)}</small>)}
                    {group.permissions.length > 3 ? <small>+{group.permissions.length - 3} more</small> : null}
                  </div>
                  {editing ? (
                    <form className="workspace-group-editor" id={`workspace-group-editor-${group.groupId}`} onSubmit={(event) => void submitGroupUpdate(event, group)}>
                      <fieldset disabled={!canManageGroups}>
                        <div className="workspace-group-editor-top">
                          <label>
                            <span>Group name</span>
                            <input
                              onChange={(event) => updateGroupDraft(group, { name: event.target.value })}
                              value={draft.name}
                            />
                          </label>
                          <span>{group.memberCount} members</span>
                        </div>
                        <label>
                          <span>Description</span>
                          <textarea
                            onChange={(event) => updateGroupDraft(group, { description: event.target.value })}
                            rows={2}
                            value={draft.description}
                          />
                        </label>
                        <PermissionGrid
                          disabled={!canManageGroups}
                          onToggle={(permission) => toggleDraftPermission(group, permission)}
                          options={availablePermissions}
                          selected={draft.permissions}
                        />
                      </fieldset>
                      <div className="workspace-group-actions">
                        <button disabled={!canManageGroups || !draft.name.trim()} type="submit">
                          <Save aria-hidden="true" size={15} />
                          Save
                        </button>
                        <button
                          disabled={!canManageGroups || lockedAdminDelete}
                          onClick={() => void removeGroup(group)}
                          type="button"
                        >
                          <Trash2 aria-hidden="true" size={15} />
                          Delete
                        </button>
                      </div>
                    </form>
                  ) : null}
                </article>
              )
            })}
          </div>
        </section>
      </div>

      <section className="panel workspace-admin-list" aria-labelledby="workspace-invitations-title">
        <div className="workspace-section-heading">
          <Link2 aria-hidden="true" size={18} />
            <div>
              <h3 id="workspace-invitations-title">Invitations</h3>
              <p>Pending invite links do not grant access until a signed-in account opens and accepts them.</p>
            </div>
          </div>
        <div className="workspace-invitation-list">
          {workspaceAdmin.invitations.map((invitation) => (
            <article className="workspace-invitation-row" key={invitation.invitationId}>
              <a href={invitationLink(invitation)}>{invitationLink(invitation)}</a>
              <span>{invitation.status}</span>
              <small>{groupListLabel(invitation.groupIds, workspaceAdmin.groups)}</small>
              <time dateTime={invitation.expiresAt}>Expires {formatDate(invitation.expiresAt)}</time>
            </article>
          ))}
        </div>
      </section>
    </div>
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

function PermissionGrid({
  disabled,
  onToggle,
  options,
  selected,
}: {
  disabled: boolean
  onToggle: (permission: string) => void
  options: WorkspacePermissionOption[]
  selected: string[]
}) {
  return (
    <div className="workspace-permission-grid">
      {options.map((option) => (
        <label className="workspace-permission-option" key={option.permission}>
          <input
            checked={selected.includes(option.permission)}
            disabled={disabled}
            onChange={() => onToggle(option.permission)}
            type="checkbox"
          />
          <span>
            <strong>{option.label}</strong>
            <small>{option.permission}</small>
          </span>
        </label>
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

function permissionLabel(permission: string, options: WorkspacePermissionOption[]) {
  return options.find((option) => option.permission === permission)?.label ?? permission
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
