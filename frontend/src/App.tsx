import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { SignInGate } from './components/SignInGate'
import { AuthProvider } from './data/AuthContext'
import { DataProvider } from './data/DataProvider'
import { I18nProvider } from './i18n'
import { AuditPage } from './pages/AuditPage'
import { DashboardPage } from './pages/DashboardPage'
import { EvaluationPage } from './pages/EvaluationPage'
import { FindingDetailPage } from './pages/FindingDetailPage'
import { FindingsPage } from './pages/FindingsPage'
import { GovernancePage } from './pages/GovernancePage'
import { HomePage } from './pages/HomePage'
import { SourcesPage } from './pages/SourcesPage'
import { WorkspaceAdminPage } from './pages/WorkspaceAdminPage'
import { WorkspaceGroupsPage } from './pages/WorkspaceGroupsPage'
import { WorkspaceInvitationPage } from './pages/WorkspaceInvitationPage'
import { WorkspaceMembersPage } from './pages/WorkspaceMembersPage'
import {
  AccountPage,
  ChangelogPage,
  DocsPage,
  FeedbackPage,
  HelpPage,
  PlanPage,
  PlatformStatusPage,
  SessionBoundaryPage,
} from './pages/SupportPages'

function App() {
  return (
    <I18nProvider>
      <BrowserRouter>
        <Routes>
          <Route index element={<HomePage />} />
          <Route element={<ConsoleRoot />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="workspace/admin" element={<WorkspaceAdminPage />} />
            <Route path="workspace/admin/groups" element={<WorkspaceGroupsPage />} />
            <Route path="workspace/admin/members" element={<WorkspaceMembersPage />} />
            <Route path="workspace/invitations/:invitationId" element={<WorkspaceInvitationPage />} />
            <Route path="sources" element={<SourcesPage />} />
            <Route path="findings" element={<FindingsPage />} />
            <Route path="findings/:findingId" element={<FindingDetailPage />} />
            <Route path="audit" element={<AuditPage />} />
            <Route path="evaluation" element={<EvaluationPage />} />
            <Route path="governance" element={<GovernancePage />} />
            <Route path="account" element={<AccountPage />} />
            <Route path="feedback" element={<FeedbackPage />} />
            <Route path="changelog" element={<ChangelogPage />} />
            <Route path="help" element={<HelpPage />} />
            <Route path="docs" element={<DocsPage />} />
            <Route path="status" element={<PlatformStatusPage />} />
            <Route path="plan" element={<PlanPage />} />
            <Route path="session" element={<SessionBoundaryPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </I18nProvider>
  )
}

function ConsoleRoot() {
  return (
    <AuthProvider>
      <SignInGate>
        <DataProvider>
          <AppShell />
        </DataProvider>
      </SignInGate>
    </AuthProvider>
  )
}

export default App
