import { Navigate, Route, Routes } from 'react-router-dom';

import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import { ApplicationsPage } from './pages/Applications';
import { AuditLogPage } from './pages/AuditLog';
import { DashboardPage } from './pages/Dashboard';
import { FrameworksPage } from './pages/Frameworks';
import { LoginPage } from './pages/Login';
import { NotFoundPage } from './pages/NotFound';
import { ReferenceDataPage } from './pages/ReferenceData';
import { RegisterPage } from './pages/Register';
import { ReportsPage } from './pages/Reports';
import { ReviewsPage } from './pages/Reviews';
import { ReviewWorkspacePage } from './pages/ReviewWorkspace';
import { SettingsPage } from './pages/Settings';
import { UsersPage } from './pages/Users';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/frameworks" element={<FrameworksPage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/reviews/:reviewId" element={<ReviewWorkspacePage />} />
          <Route path="/reference-data" element={<ReferenceDataPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/audit-log" element={<AuditLogPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
