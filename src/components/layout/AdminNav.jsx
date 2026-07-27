import { NavLink, Outlet } from 'react-router-dom'
import clsx from 'clsx'

const ADMIN_NAV_LINKS = [
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/reports', label: 'Reports' },
  { to: '/admin/analytics', label: 'Analytics' },
  { to: '/admin/settings', label: 'Settings' },
]

export default function AdminNav() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Admin panel</h1>
        <nav aria-label="Admin sections" className="mt-4 flex flex-wrap gap-1 border-b border-border">
          {ADMIN_NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                clsx(
                  'rounded-t-lg px-4 py-2 text-sm font-medium transition-colors',
                  isActive ? 'border-b-2 border-accent text-accent' : 'text-text hover:text-text-h'
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <Outlet />
    </div>
  )
}
