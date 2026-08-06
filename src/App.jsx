import { Routes, Route } from 'react-router-dom'
import PublicShell from './components/layout/PublicShell'
import AppShell from './components/layout/AppShell'
import AdminNav from './components/layout/AdminNav'
import ProtectedRoute from './auth/ProtectedRoute'
import AdminRoute from './auth/AdminRoute'

import WelcomePage from './pages/WelcomePage'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage'
import ResetPasswordPage from './pages/auth/ResetPasswordPage'
import ProfilePage from './pages/ProfilePage'
import ResumeUploadPage from './pages/resume/ResumeUploadPage'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import AnalysisResultsPage from './pages/AnalysisResultsPage'
import DocumentsPage from './pages/DocumentsPage'
import SkillAssessmentPage from './pages/SkillAssessmentPage'
import InterviewPracticePage from './pages/InterviewPracticePage'
import LearningRoadmapPage from './pages/LearningRoadmapPage'
import ResumeBuilderPage from './pages/ResumeBuilderPage'
import VersionHistoryPage from './pages/VersionHistoryPage'
import AdminUsersPage from './pages/admin/AdminUsersPage'
import AdminReportsPage from './pages/admin/AdminReportsPage'
import AdminAnalyticsPage from './pages/admin/AdminAnalyticsPage'
import AdminSettingsPage from './pages/admin/AdminSettingsPage'
import NotFoundPage from './pages/NotFoundPage'
import ForbiddenPage from './pages/ForbiddenPage'

export default function App() {
  return (
    <Routes>
      <Route element={<PublicShell />}>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/403" element={<ForbiddenPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route element={<AppShell />}>
        {/* Authenticated */}
        <Route element={<ProtectedRoute />}>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/resume/upload" element={<ResumeUploadPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/analysis-results" element={<AnalysisResultsPage />} />
          <Route path="/analysis-results/:id" element={<AnalysisResultsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/skill-assessment" element={<SkillAssessmentPage />} />
          <Route path="/interview-practice" element={<InterviewPracticePage />} />
          <Route path="/roadmap" element={<LearningRoadmapPage />} />
          <Route path="/resume-builder" element={<ResumeBuilderPage />} />
          <Route path="/resume/versions" element={<VersionHistoryPage />} />
        </Route>

        {/* Admin */}
        <Route element={<AdminRoute />}>
          <Route element={<AdminNav />}>
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/admin/reports" element={<AdminReportsPage />} />
            <Route path="/admin/analytics" element={<AdminAnalyticsPage />} />
            <Route path="/admin/settings" element={<AdminSettingsPage />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
