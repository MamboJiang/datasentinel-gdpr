import { ArrowLeft, Search, UsersRound } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader, StatusBadge } from '../components/ui'
import { useData } from '../data/useData'
import type { WorkspaceGroup, WorkspaceMembership } from '../types'
import './WorkspaceAdminPage.css'

type MemberSort = 'name' | 'group' | 'status' | 'joined' | 'activity'
type MemberGrouping = 'none' | 'group' | 'status'

export function WorkspaceMembersPage() {
  const { workspaceAdmin, workspaceDirectory } = useData()
  const [query, setQuery] = useState('')
  const [groupFilter, setGroupFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState<MemberSort>('name')
  const [grouping, setGrouping] = useState<MemberGrouping>('none')
  const groups = workspaceAdmin.groups
  const workspace = workspaceAdmin.workspace
  const canViewAdmin = workspaceAdmin.permissionBoundary.allowedActions.includes('view_workspace_admin')

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

  return (
    <div className="workspace-members-page">
      <PageHeader
        eyebrow="Workspace admin"
        title="Members"
        description="Search, filter, group, and sort every member in this Workspace."
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
                <table className="workspace-member-table">
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Groups</th>
                      <th>Status</th>
                      <th>Joined</th>
                      <th>Last active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {section.members.map((member) => (
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
                          <span className="workspace-role-stack">
                            {member.groupIds.length > 0
                              ? member.groupIds.map((groupId) => <small key={groupId}>{groupLabel(groupId, groups)}</small>)
                              : <small>No groups</small>}
                          </span>
                        </td>
                        <td><StatusBadge value={member.status} /></td>
                        <td>{formatDate(member.joinedAt)}</td>
                        <td>{formatDate(member.lastActiveAt)}</td>
                      </tr>
                    ))}
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
