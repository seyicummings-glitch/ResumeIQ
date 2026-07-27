import { Navigate, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from './AuthContext'
import { pingAdminOnly } from '../api/auth'
import Spinner from '../components/ui/Spinner'

/**
 * Gated on the client-side role for a fast redirect, then double-checked
 * live against the backend's real GET /auth/admin-only route — mirrors the
 * backend's own require_admin dependency instead of trusting local state alone.
 */
export default function AdminRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth()

  const adminCheck = useQuery({
    queryKey: ['admin-only-check'],
    queryFn: pingAdminOnly,
    enabled: isAuthenticated && isAdmin,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner label="Checking your session…" />
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!isAdmin) return <Navigate to="/403" replace />

  if (adminCheck.isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner label="Verifying admin access…" />
      </div>
    )
  }

  if (adminCheck.isError) return <Navigate to="/403" replace />

  return <Outlet />
}
