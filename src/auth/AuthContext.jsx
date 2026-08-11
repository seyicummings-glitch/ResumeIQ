import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import * as authApi from '../api/auth'
import { setUnauthorizedHandler } from '../api/client'
import { getToken, setToken, clearToken, isTokenExpired } from './tokenStorage'

const AuthContext = createContext(null)

// Admin "view as user" mode — a pure presentation toggle, not a real
// permission change. The admin's JWT/role/session never change; this just
// controls what the frontend shows/routes to. Persisted per-tab (not
// localStorage) so a reload during testing doesn't kick the admin back to
// the admin view, but it naturally clears when the tab closes or on logout.
const VIEW_MODE_KEY = 'resumeiq_admin_view_mode'

function getStoredViewMode() {
  return sessionStorage.getItem(VIEW_MODE_KEY) === 'user' ? 'user' : 'admin'
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [viewMode, setViewMode] = useState(getStoredViewMode)
  const navigate = useNavigate()

  const handleUnauthorized = useCallback(() => {
    setUser(null)
    navigate('/login?sessionExpired=1')
  }, [navigate])

  useEffect(() => {
    setUnauthorizedHandler(handleUnauthorized)
  }, [handleUnauthorized])

  useEffect(() => {
    const token = getToken()
    if (!token || isTokenExpired(token)) {
      clearToken()
      setIsLoading(false)
      return
    }
    authApi
      .getMe()
      .then(setUser)
      .catch(() => {
        clearToken()
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async ({ email, password }) => {
    const { access_token: accessToken } = await authApi.login({ email, password })
    setToken(accessToken)
    const me = await authApi.getMe()
    setUser(me)
    return me
  }, [])

  const register = useCallback(
    async ({ email, password, fullName }) => {
      await authApi.register({ email, password, fullName })
      // Backend's /register doesn't return a token, so log in right after
      // with the same credentials to land the user already authenticated.
      return login({ email, password })
    },
    [login]
  )

  const logout = useCallback(() => {
    authApi.logout().catch(() => {})
    clearToken()
    setUser(null)
    sessionStorage.removeItem(VIEW_MODE_KEY)
    setViewMode('admin')
  }, [])

  const switchToUserView = useCallback(() => {
    sessionStorage.setItem(VIEW_MODE_KEY, 'user')
    setViewMode('user')
    navigate('/dashboard')
  }, [navigate])

  const switchToAdminView = useCallback(() => {
    sessionStorage.removeItem(VIEW_MODE_KEY)
    setViewMode('admin')
    navigate('/admin')
  }, [navigate])

  const refreshUser = useCallback(async () => {
    const me = await authApi.getMe()
    setUser(me)
    return me
  }, [])

  const isAdmin = user?.role === 'admin'

  const value = {
    user,
    isAuthenticated: Boolean(user),
    isAdmin,
    // Effective admin state for nav/route gating — false while an admin has
    // switched to "view as user" mode, even though their real role is still admin.
    isAdminView: isAdmin && viewMode === 'admin',
    viewMode,
    switchToUserView,
    switchToAdminView,
    isLoading,
    login,
    register,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
