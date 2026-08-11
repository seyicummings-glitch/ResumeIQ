import { Outlet } from 'react-router-dom'
import { UserRoundCog } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import Button from '../ui/Button'

// The admin section's own navigation (Overview/People/Subscriptions/etc.)
// lives in the main Sidebar (see Sidebar.jsx's ADMIN_NAV_GROUPS) so there's
// one sidebar that switches modes, not a second nav column rendered here
// next to it. This wrapper just supplies the page header and the view-switch
// control, then hands off to whichever admin page is routed.
export default function AdminNav() {
  const { user, switchToUserView } = useAuth()

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-text-h">Admin panel</h1>
          <p className="mt-1 text-sm text-text">Signed in as {user?.full_name || user?.email}</p>
        </div>
        <Button variant="secondary" size="sm" onClick={switchToUserView}>
          <UserRoundCog size={14} aria-hidden="true" />
          Switch to User View
        </Button>
      </div>

      <Outlet />
    </div>
  )
}
