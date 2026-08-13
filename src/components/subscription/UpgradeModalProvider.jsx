import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { setFeatureLimitHandler, setBalanceChangedHandler } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import UpgradeModal from './UpgradeModal'

const UpgradeModalContext = createContext(null)

/**
 * Mounts the single, app-wide "AI Usage Limit Reached" modal (see UpgradeModal.jsx) and wires it
 * to fire automatically whenever any gated AI feature hits its token limit (api/client.js calls
 * back into this on any 402) — no individual page needs to catch that itself. Also refreshes the
 * token balance display right after any gated feature successfully spends tokens, so it updates
 * without a page reload.
 */
export function UpgradeModalProvider({ children }) {
  const [detail, setDetail] = useState(null)
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuth()

  const openUpgradeModal = useCallback((nextDetail) => setDetail(nextDetail || {}), [])
  const closeUpgradeModal = useCallback(() => setDetail(null), [])

  useEffect(() => {
    setFeatureLimitHandler((payload) => setDetail(payload || {}))
    setBalanceChangedHandler(() => {
      queryClient.invalidateQueries({ queryKey: ['subscription', 'me'] })
    })
    return () => {
      setFeatureLimitHandler(null)
      setBalanceChangedHandler(null)
    }
  }, [queryClient])

  // Only a logged-in account can hit a token limit or have a balance to show — mounting the
  // modal (and the plan/balance queries it fetches) only once authenticated keeps public pages
  // (landing, login, register) from firing doomed authenticated requests in the background.
  return (
    <UpgradeModalContext.Provider value={{ openUpgradeModal, closeUpgradeModal }}>
      {children}
      {isAuthenticated && <UpgradeModal detail={detail} onClose={closeUpgradeModal} />}
    </UpgradeModalContext.Provider>
  )
}

/** @returns {{ openUpgradeModal: (detail?: object) => void, closeUpgradeModal: () => void }} */
export function useUpgradeModal() {
  const ctx = useContext(UpgradeModalContext)
  if (!ctx) throw new Error('useUpgradeModal must be used within an UpgradeModalProvider')
  return ctx
}
