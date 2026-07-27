import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import * as authApi from '../api/auth'
import { setUnauthorizedHandler } from '../api/client'
import { getToken, setToken, clearToken, isTokenExpired } from './tokenStorage'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
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
  }, [])

  const refreshUser = useCallback(async () => {
    const me = await authApi.getMe()
    setUser(me)
    return me
  }, [])

  const value = {
    user,
    isAuthenticated: Boolean(user),
    isAdmin: user?.role === 'admin',
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
