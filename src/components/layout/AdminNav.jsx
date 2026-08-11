import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Users, Flag, BarChart3, Settings, CreditCard, GraduationCap } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../auth/AuthContext'

// Grows across the admin panel build-out — each wave adds its own group/leaf
// once the page it links to actually exists, so there are never dead links.
const ADMIN_NAV_GROUPS = [
  {
    label: 'Overview',
    items: [{ to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true }],
  },
  {
    label: 'People',
    items: [{ to: '/admin/users', label: 'Users', icon: Users }],
  },
  {
    label: 'Subscriptions',
    items: [{ to: '/admin/subscriptions/plans', label: 'Plans', icon: CreditCard }],
  },
  {
    label: 'Content & Activity',
    items: [{ to: '/admin/skill-resources', label: 'Skill Resources', icon: GraduationCap }],
  },
  {
    label: 'Insights',
    items: [{ to: '/admin/analytics', label: 'Analytics', icon: BarChart3 }],
  },
  {
    label: 'Support',
    items: [{ to: '/admin/reports', label: 'Reports', icon: Flag }],
  },
  {
    label: 'Configuration',
    items: [{ to: '/admin/settings', label: 'Settings', icon: Settings }],
  },
]

export default function AdminNav() {
  const { user } = useAuth()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Admin panel</h1>
        <p className="mt-1 text-sm text-text">Signed in as {user?.full_name || user?.email}</p>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <nav aria-label="Admin sections" className="flex shrink-0 flex-col gap-5 lg:w-56">
          {ADMIN_NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="px-3 text-[11px] font-semibold uppercase tracking-wide text-text/60">{group.label}</p>
              <div className="mt-1 flex flex-col gap-0.5">
                {group.items.map(({ to, label, icon: Icon, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    className={({ isActive }) =>
                      clsx(
                        'flex items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors',
                        isActive ? 'bg-accent/[0.14] text-accent' : 'text-text hover:bg-border/40 hover:text-text-h'
                      )
                    }
                  >
                    <Icon size={16} strokeWidth={1.8} className="shrink-0" aria-hidden="true" />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="min-w-0 flex-1">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
