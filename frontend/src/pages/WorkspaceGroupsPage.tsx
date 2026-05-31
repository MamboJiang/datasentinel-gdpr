import { ArrowLeft, Pencil, Plus, Save, ShieldCheck, Trash2, X } from 'lucide-react'
import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader } from '../components/ui'
import { useData } from '../data/useData'
import type { WorkspaceGroup, WorkspacePermissionOption } from '../types'
import './WorkspaceAdminPage.css'

type GroupDraft = {
  description: string
  name: string
  permissions: string[]
}

export function WorkspaceGroupsPage() {
  const {
    createWorkspaceGroup,
    deleteWorkspaceGroup,
    updateWorkspaceGroup,
    workspaceAdmin,
    workspaceDirectory,
  } = useData()
  const [createGroupOpen, setCreateGroupOpen] = useState(false)
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null)
  const [groupDrafts, setGroupDrafts] = useState<Record<string, GroupDraft>>({})
  const [newGroupDescription, setNewGroupDescription] = useState('')
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupPermissions, setNewGroupPermissions] = useState<string[]>(['view_assigned_findings'])
  const workspace = workspaceAdmin.workspace
  const canViewAdmin = workspaceAdmin.permissionBoundary.allowedActions.includes('view_workspace_admin')
  const canManageGroups = workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_groups')
  const canManageOwnership = workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_ownership')
  const availablePermissions = workspaceAdmin.availablePermissions
  const protectedGroupCount = workspaceAdmin.groups.filter((group) => group.groupId === 'workspace_owner' || group.groupId === 'workspace_admin').length
  const customGroupCount = Math.max(0, workspaceAdmin.groups.length - protectedGroupCount)
  const totalPermissionAssignments = workspaceAdmin.groups.reduce((total, group) => total + group.permissions.length, 0)

  if (!workspaceDirectory.currentWorkspaceId && workspaceDirectory.workspaceRequired) {
    return <EmptyState title="Workspace required" description="Accept a Workspace invitation or create a Workspace before managing groups." />
  }

  if (!workspace || !canViewAdmin) {
    return <EmptyState title="Group controls unavailable" description="Your current Workspace groups do not include administrator visibility." />
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
      setGroupDrafts((current) => {
        const remaining = { ...current }
        delete remaining[group.groupId]
        return remaining
      })
      setEditingGroupId((current) => current === group.groupId ? null : current)
    }
  }

  return (
    <div className="workspace-groups-page">
      <PageHeader
        eyebrow="Workspace admin"
        title="Group controls"
        description={canManageGroups ? 'Create, rename, and permission Workspace groups.' : 'Inspect Workspace group definitions and permission boundaries.'}
        actions={<Link className="button button-secondary" to="/workspace/admin"><ArrowLeft aria-hidden="true" size={16} /> Admin</Link>}
      />

      <section className="workspace-members-summary" aria-label="Group summary">
        <SummaryTile label="Groups" value={workspaceAdmin.groups.length} />
        <SummaryTile label="Custom groups" value={customGroupCount} />
        <SummaryTile label="Protected groups" value={protectedGroupCount} />
        <SummaryTile label="Permission grants" value={totalPermissionAssignments} />
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
        <DeniedGroupActions />
        <div className="workspace-group-list">
          {workspaceAdmin.groups.map((group) => {
            const draft = draftForGroup(group)
            const editing = editingGroupId === group.groupId
            const ownerGroup = group.groupId === 'workspace_owner'
            const lockedGroupDelete = ownerGroup || group.groupId === 'workspace_admin'
            const groupEditingDisabled = !canManageGroups || (ownerGroup && !canManageOwnership)
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
                    disabled={groupEditingDisabled}
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
                    <fieldset disabled={groupEditingDisabled}>
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
                        disabled={groupEditingDisabled}
                        onToggle={(permission) => toggleDraftPermission(group, permission)}
                        options={availablePermissions}
                        selected={draft.permissions}
                      />
                    </fieldset>
                    <div className="workspace-group-actions">
                      <button disabled={groupEditingDisabled || !draft.name.trim()} type="submit">
                        <Save aria-hidden="true" size={15} />
                        Save
                      </button>
                      <button
                        disabled={groupEditingDisabled || lockedGroupDelete}
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
  )
}

function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <span>
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
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

function DeniedGroupActions() {
  const { workspaceAdmin } = useData()
  const relevantDenials = workspaceAdmin.permissionBoundary.deniedActions.filter((item) => (
    item.action.includes('workspace_group') || item.action === 'manage_workspace_groups'
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

function permissionLabel(permission: string, options: WorkspacePermissionOption[]) {
  return options.find((option) => option.permission === permission)?.label ?? permission
}
