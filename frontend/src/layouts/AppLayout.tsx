import {
  ClipboardCheck,
  Database,
  FileText,
  LayoutDashboard,
  LogOut,
  ScrollText,
  Server,
  Settings,
  Shield,
  Users
} from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { logout } from '../lib/auth';
import { useAuthStore } from '../stores/authStore';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/reviews', label: 'Reviews', icon: ClipboardCheck },
  { to: '/frameworks', label: 'Frameworks', icon: Shield },
  { to: '/applications', label: 'Applications', icon: Server },
  { to: '/reference-data', label: 'Reference Data', icon: Database },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/audit-log', label: 'Audit Log', icon: ScrollText },
  { to: '/users', label: 'Users', icon: Users },
  { to: '/settings', label: 'Settings', icon: Settings }
];

export function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to main content
      </a>
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[280px_1fr]">
        <aside className="border-r border-slate-200 bg-white p-4">
          <div className="mb-6">
            <p className="text-xs uppercase tracking-[0.16em] text-brand-700">Security Analyst Platform</p>
            <h2 className="text-xl font-bold text-slate-900">SAP v3</h2>
          </div>

          <nav className="space-y-1" aria-label="Primary navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-3 py-2 text-sm font-medium transition-colors ${
                      isActive ? 'bg-brand-100 text-brand-900' : 'text-slate-700 hover:bg-slate-100'
                    }`
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          <div className="mt-8 rounded border border-slate-200 bg-slate-50 p-3 text-xs">
            <p className="font-semibold text-slate-700">Signed in</p>
            <p className="mt-1 text-slate-600">{user?.name}</p>
            <p className="text-slate-500">{user?.role}</p>
            <button
              onClick={handleLogout}
              className="mt-3 inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              <LogOut className="h-3 w-3" />
              Sign out
            </button>
          </div>
        </aside>

        <main id="main-content" className="p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
