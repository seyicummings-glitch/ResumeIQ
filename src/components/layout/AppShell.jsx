import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Sun, Moon, User, Shield } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useTheme } from '../../theme/ThemeContext'
import SkipToContentLink from './SkipToContentLink'
import Sidebar, { NAV_ITEMS } from './Sidebar'
import GlobalCareerCoach from '../coach/GlobalCareerCoach'
import Button from '../ui/Button'

export default function AppShell() {
  const { user, isAdmin, switchToAdminView } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const isLight = theme === 'light'
  const onAdminPages = location.pathname.startsWith('/admin')

  const currentLabel = NAV_ITEMS.find((item) => location.pathname.startsWith(item.to))?.label ?? 'ResumeIQ'

  return (
    <div className="flex min-h-screen bg-bg text-text">
      <SkipToContentLink />
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center justify-between border-b border-border bg-bg px-6">
            <span className="font-mono text-xs text-text">{currentLabel}</span>
            <div className="flex items-center gap-2">
              {isAdmin && !onAdminPages && (
                <Button variant="secondary" size="sm" onClick={switchToAdminView}>
                  <Shield size={14} aria-hidden="true" />
                  Switch to Admin View
                </Button>
              )}
              <button
                type="button"
                onClick={toggle}
                title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
                className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-text transition-colors hover:bg-border/40"
              >
                {isLight ? <Moon size={14} aria-hidden="true" /> : <Sun size={14} aria-hidden="true" />}
              </button>
              <button
                type="button"
                onClick={() => navigate('/profile')}
                title="My profile"
                className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-text transition-colors hover:bg-border/40"
              >
                <User size={14} aria-hidden="true" />
              </button>
              <div
                className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-xs font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #4f46e5, var(--accent-2))' }}
                onClick={() => navigate('/profile')}
                aria-hidden="true"
              >
                {(user?.full_name || user?.email || '?')[0].toUpperCase()}
              </div>
            </div>
        </header>
        <main id="main-content" tabIndex={-1} className="w-full flex-1 px-6 py-8">
          <Outlet />
        </main>
      </div>
      <GlobalCareerCoach />
    </div>
  )
}
