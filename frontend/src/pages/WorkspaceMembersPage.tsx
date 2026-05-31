import { ArrowLeft, Check, Pencil, Search, Trash2, UsersRound, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader, StatusBadge } from '../components/ui'
import { useData } from '../data/useData'
import type { WorkspaceGroup, WorkspaceMembership } from '../types'
import './WorkspaceAdminPage.css'

type MemberSort = 'name' | 'group' | 'status' | 'joined' | 'activity'
type MemberGrouping = 'none' | 'group' | 'status'

export function WorkspaceMembersPage() {
  const { deleteWorkspaceMember, updateWorkspaceMember, workspaceAdmin, workspaceDirectory } = useData()
  const [query, setQuery] = useState('')
  const [groupFilter, setGroupFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState<MemberSort>('name')
  const [grouping, setGrouping] = useState<MemberGrouping>('none')
  const [editingMemberId, setEditingMemberId] = useState<string | null>(null)
  const [draftGroupIds, setDraftGroupIds] = useState<string[]>([])
  const groups = workspaceAdmin.groups
  const workspace = workspaceAdmin.workspace
  const canViewAdmin = workspaceAdmin.permissionBoundary.allowedActions.includes('view_workspace_admin')
  const canManageMembers = workspaceAdmin.permissionBoundary.allowedActions.includes('manage_workspace_members')
  const currentAccountId = workspaceAdmin.currentMembership?.accountId

  const filteredMembers = useMemo(() => {
    return workspaceAdmin.members
      .filter((member) => {
        const text = `${member.displayName} ${member.email ?? ''} ${member.accountId}`.toLowerCase()
        const matchesQuery = text.includes(query.toLowerCase())
        const matchesGroup = groupFilter === 'all' || member.groupIds.includes(groupFilter)
        const matchesStatus = statusFilter === 'all' || member.status === statusFilter
        return matchesQuery && matchesGroup && matchesStatus
      })
      .sort((left, right) => compareMembers(left, right, sortBy, groups))
  }, [groupFilter, groups, query, sortBy, statusFilter, workspaceAdmin.members])

  const groupedMembers = useMemo(() => groupMembers(filteredMembers, grouping, groups), [filteredMembers, grouping, groups])
  const statusOptions = Array.from(new Set(workspaceAdmin.members.map((member) => member.status))).sort()

  if (!workspaceDirectory.currentWorkspaceId && workspaceDirectory.workspaceRequired) {
    return <EmptyState title="Workspace required" description="Accept a Workspace invitation or create a Workspace before viewing members." />
  }

  if (!workspace || !canViewAdmin) {
    return <EmptyState title="Members unavailable" description="Your current Workspace groups do not include administrator visibility." />
  }

  function startMemberEdit(member: WorkspaceMembership) {
    setEditingMemberId(member.membershipId)
    setDraftGroupIds(member.groupIds)
  }

  function cancelMemberEdit() {
    setEditingMemberId(null)
    setDraftGroupIds([])
  }

  function toggleDraftGroup(groupId: string) {
    setDraftGroupIds((current) => (
      current.includes(groupId)
        ? current.filter((item) => item !== groupId)
        : [...current, groupId]
    ))
  }

  async function saveMemberGroups(member: WorkspaceMembership) {
    const updated = await updateWorkspaceMember({
      groupIds: draftGroupIds,
      membershipId: member.membershipId,
      workspaceId: member.workspaceId,
    })
    if (updated) {
      cancelMemberEdit()
    }
  }

  async function removeMember(member: WorkspaceMembership) {
    if (!window.confirm(`Remove ${member.displayName} from this Workspace?`)) {
      return
    }

    const removed = await deleteWorkspaceMember({
      membershipId: member.membershipId,
      workspaceId: member.workspaceId,
    })
    if (removed && editingMemberId === member.membershipId) {
      cancelMemberEdit()
    }
  }

  return (
    <div className="workspace-members-page">
      <PageHeader
        eyebrow="Workspace admin"
        title="Members"
        actions={<Link className="button button-secondary" to="/workspace/admin"><ArrowLeft aria-hidden="true" size={16} /> Admin</Link>}
      />

      <section className="panel workspace-member-controls" aria-label="Member filters">
        <label className="search-field workspace-member-search">
          <Search aria-hidden="true" size={17} />
          <span className="sr-only">Search members</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, email, or account" />
        </label>
        <label>
          <span>Group</span>
          <select value={groupFilter} onChange={(event) => setGroupFilter(event.target.value)}>
            <option value="all">All groups</option>
            {groups.map((group) => <option key={group.groupId} value={group.groupId}>{group.name}</option>)}
          </select>
        </label>
        <label>
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All statuses</option>
            {statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <label>
          <span>Sort</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as MemberSort)}>
            <option value="name">Name</option>
            <option value="group">Primary group</option>
            <option value="status">Status</option>
            <option value="joined">Joined date</option>
            <option value="activity">Last active</option>
          </select>
        </label>
        <label>
          <span>Group by</span>
          <select value={grouping} onChange={(event) => setGrouping(event.target.value as MemberGrouping)}>
            <option value="none">None</option>
            <option value="group">Group</option>
            <option value="status">Status</option>
          </select>
        </label>
      </section>

      <section className="workspace-members-summary" aria-label="Member summary">
        <SummaryTile label="Visible members" value={filteredMembers.length} />
        <SummaryTile label="Total members" value={workspaceAdmin.members.length} />
        <SummaryTile label="Groups" value={groups.length} />
        <SummaryTile label="Statuses" value={statusOptions.length} />
      </section>

      {filteredMembers.length ? (
        <div className="workspace-member-directory">
          {groupedMembers.map((section) => (
            <section className="panel workspace-member-section" key={section.label}>
              <div className="workspace-section-heading">
                <UsersRound aria-hidden="true" size={18} />
                <div>
                  <h3>{section.label}</h3>
                  <p>{section.members.length} member{section.members.length === 1 ? '' : 's'}</p>
                </div>
              </div>
              <div className="workspace-member-table-wrap">
                <table className={`workspace-member-table${canManageMembers ? ' workspace-member-table-actions' : ''}`}>
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Groups</th>
                      <th>Status</th>
                      <th>Joined</th>
                      <th>Last active</th>
                      {canManageMembers ? <th>Actions</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {section.members.map((member) => {
                      const editing = editingMemberId === member.membershipId
                      const selfMember = member.accountId === currentAccountId
                      const saveDisabled = draftGroupIds.length === 0 || sameGroups(draftGroupIds, member.groupIds)

                      return (
                        <tr key={member.membershipId}>
                          <td>
                            <div className="workspace-member-identity">
                              <span className="workspace-member-avatar" aria-hidden="true">{initials(member.displayName)}</span>
                              <span>
                                <strong>{member.displayName}</strong>
                                <small>{member.email ?? member.accountId}</small>
                              </span>
                            </div>
                          </td>
                          <td>
                            {editing ? (
                              <div className="workspace-member-group-editor" aria-label={`${member.displayName} groups`}>
                                {groups.map((group) => (
                                  <label key={group.groupId}>
                                    <input
                                      checked={draftGroupIds.includes(group.groupId)}
                                      onChange={() => toggleDraftGroup(group.groupId)}
                                      type="checkbox"
                                    />
                                    <span>{group.name}</span>
                                  </label>
                                ))}
                              </div>
                            ) : (
                              <span className="workspace-role-stack">
                                {member.groupIds.length > 0
                                  ? member.groupIds.map((groupId) => <small key={groupId}>{groupLabel(groupId, groups)}</small>)
                                  : <small>No groups</small>}
                              </span>
                            )}
                          </td>
                          <td><StatusBadge value={member.status} /></td>
                          <td>{formatDate(member.joinedAt)}</td>
                          <td>{formatDate(member.lastActiveAt)}</td>
                          {canManageMembers ? (
                            <td>
                              <div className="workspace-member-actions">
                                {editing ? (
                                  <>
                                    <button aria-label={`Save groups for ${member.displayName}`} disabled={saveDisabled} onClick={() => { void saveMemberGroups(member) }} title="Save groups" type="button">
                                      <Check aria-hidden="true" size={15} />
                                    </button>
                                    <button aria-label={`Cancel editing ${member.displayName}`} onClick={cancelMemberEdit} title="Cancel" type="button">
                                      <X aria-hidden="true" size={15} />
                                    </button>
                                  </>
                                ) : (
                                  <button aria-label={`Edit groups for ${member.displayName}`} onClick={() => startMemberEdit(member)} title="Edit groups" type="button">
                                    <Pencil aria-hidden="true" size={15} />
                                  </button>
                                )}
                                <button aria-label={`Remove ${member.displayName}`} disabled={selfMember} onClick={() => { void removeMember(member) }} title={selfMember ? 'You cannot remove your own active membership' : 'Remove member'} type="button">
                                  <Trash2 aria-hidden="true" size={15} />
                                </button>
                              </div>
                            </td>
                          ) : null}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>
      ) : <EmptyState title="No members match these filters" />}
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

function groupMembers(members: WorkspaceMembership[], grouping: MemberGrouping, groups: WorkspaceGroup[]) {
  if (grouping === 'group') {
    return groups
      .map((group) => ({
        label: group.name,
        members: members.filter((member) => member.groupIds.includes(group.groupId)),
      }))
      .filter((section) => section.members.length > 0)
  }

  if (grouping === 'status') {
    return Array.from(new Set(members.map((member) => member.status))).sort()
      .map((status) => ({ label: status, members: members.filter((member) => member.status === status) }))
  }

  return [{ label: 'All members', members }]
}

function compareMembers(left: WorkspaceMembership, right: WorkspaceMembership, sortBy: MemberSort, groups: WorkspaceGroup[]) {
  if (sortBy === 'group') {
    return groupLabel(left.groupIds[0] ?? '', groups).localeCompare(groupLabel(right.groupIds[0] ?? '', groups))
      || left.displayName.localeCompare(right.displayName)
  }
  if (sortBy === 'status') {
    return left.status.localeCompare(right.status) || left.displayName.localeCompare(right.displayName)
  }
  if (sortBy === 'joined') {
    return timestamp(right.joinedAt) - timestamp(left.joinedAt)
  }
  if (sortBy === 'activity') {
    return timestamp(right.lastActiveAt) - timestamp(left.lastActiveAt)
  }
  return left.displayName.localeCompare(right.displayName)
}

function groupLabel(groupId: string, groups: WorkspaceGroup[]) {
  return groups.find((group) => group.groupId === groupId)?.name ?? groupId
}

function sameGroups(left: string[], right: string[]) {
  if (left.length !== right.length) {
    return false
  }
  const rightSet = new Set(right)
  return left.every((item) => rightSet.has(item))
}

function initials(value: string) {
  const letters = value.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('')
  return letters || 'WS'
}

function formatDate(value?: string | null) {
  if (!value) {
    return 'Not available'
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(parsed)
}

function timestamp(value?: string | null) {
  if (!value) {
    return 0
  }
  const parsed = new Date(value).getTime()
  return Number.isNaN(parsed) ? 0 : parsed
}
