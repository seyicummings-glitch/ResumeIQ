import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Upload, Clock, User, Shield, LogOut, ChevronLeft, ChevronRight, FolderOpen, Brain, MessageSquare, Map, Sparkles, GitCompare, BarChart3 } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../auth/AuthContext'
import Logo from './Logo'

export const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/resume/upload', label: 'Analyze Resume', icon: Upload },
  { to: '/analysis-results', label: 'Analysis Results', icon: BarChart3 },
  { to: '/skill-assessment', label: 'Skill Assessment', icon: Brain },
  { to: '/resume-builder', label: 'AI Resume Builder', icon: Sparkles },
  { to: '/roadmap', label: 'Learning Roadmap', icon: Map },
  { to: '/interview-practice', label: 'Interview Practice', icon: MessageSquare },
  { to: '/history', label: 'Analysis History', icon: Clock },
  { to: '/resume/versions', label: 'Version History', icon: GitCompare },
  { to: '/documents', label: 'Documents', icon: FolderOpen },
  { to: '/profile', label: 'My Profile', icon: User },
  { to: '/admin/users', label: 'Admin panel', icon: Shield, adminOnly: true },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const visibleNav = NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === 'admin')

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <aside
      className={clsx(
        'sticky top-0 flex h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200',
        collapsed ? 'w-14' : 'w-56'
      )}
    >
      <div className={clsx('flex h-14 shrink-0 items-center border-b border-border', collapsed ? 'justify-center px-0' : 'px-4')}>
        <Logo collapsed={collapsed} />
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2" aria-label="Main">
        {visibleNav.map(({ to, label, icon: Icon, adminOnly }) => (
          <NavLink
            key={to}
            to={to}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent/[0.14] text-accent'
                  : adminOnly
                    ? 'text-danger/80 hover:bg-danger-bg hover:text-danger'
                    : 'text-text hover:bg-border/40 hover:text-text-h'
              )
            }
          >
            <Icon size={16} strokeWidth={1.8} className="shrink-0" aria-hidden="true" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="flex flex-col gap-0.5 border-t border-border p-2">
        {!collapsed && (
          <div className="flex items-center gap-2.5 px-2 py-2">
            <div
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
              style={{ background: 'linear-gradient(135deg, #4f46e5, var(--accent-2))' }}
              aria-hidden="true"
            >
              {(user?.full_name || user?.email || '?')[0].toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <div className="truncate text-xs font-semibold text-text-h">{user?.full_name || user?.email}</div>
              <div className="truncate font-mono text-[10px] text-text">{user?.role}</div>
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={handleLogout}
          title={collapsed ? 'Log out' : undefined}
          className="flex items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-2 text-left text-sm text-text transition-colors hover:bg-danger-bg hover:text-danger"
        >
          <LogOut size={15} className="shrink-0" aria-hidden="true" />
          {!collapsed && <span>Log out</span>}
        </button>
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={clsx(
            'flex items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-2 text-sm text-text transition-colors hover:bg-border/40 hover:text-text-h',
            collapsed && 'justify-center'
          )}
        >
          {collapsed ? <ChevronRight size={15} aria-hidden="true" /> : <ChevronLeft size={15} aria-hidden="true" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
