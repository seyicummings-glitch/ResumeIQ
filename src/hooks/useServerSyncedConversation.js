import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getAiConversation, saveAiConversation, clearAiConversation } from '../api/aiConversations'

const SAVE_DEBOUNCE_MS = 500

/**
 * Generic "conversation state that lives on the account, not just this browser tab" — shared by
 * the AI Resume Builder and Career Coach Contexts so a conversation started on one device
 * continues on another instead of vanishing on refresh or logging in elsewhere. Hydrates once
 * per login from the server, then saves in the background (debounced, not on every keystroke)
 * after each change. Only `messages` and `extra` (feature-specific state like the Resume
 * Builder's draft) are persisted — callers keep purely local UI state (an open/closed flag, a
 * transient error message) out of this and manage it themselves.
 *
 * @param {'resume_builder'|'career_coach'} kind
 */
export function useServerSyncedConversation(kind) {
  const { isAuthenticated } = useAuth()
  const [state, setState] = useState({ messages: [], extra: null })
  const [hydrated, setHydrated] = useState(false)
  const saveTimerRef = useRef(null)

  useEffect(() => {
    if (!isAuthenticated) {
      setHydrated(true)
      return
    }
    let cancelled = false
    getAiConversation(kind)
      .then((saved) => {
        if (cancelled) return
        setState({ messages: saved.messages || [], extra: saved.extra || null })
      })
      .catch(() => {
        // No saved conversation yet (or a transient network error) — starting blank is the
        // right default either way, so this is deliberately silent.
      })
      .finally(() => {
        if (!cancelled) setHydrated(true)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, kind])

  function persist(nextState) {
    if (!isAuthenticated) return
    clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      saveAiConversation(kind, nextState).catch(() => {
        // Best-effort — the user's local session still has the latest state either way; it
        // just won't have followed them to another device until the next successful save.
      })
    }, SAVE_DEBOUNCE_MS)
  }

  function updateState(patch) {
    setState((current) => {
      const next = { ...current, ...patch }
      persist(next)
      return next
    })
  }

  function clearState() {
    setState({ messages: [], extra: null })
    clearTimeout(saveTimerRef.current)
    if (isAuthenticated) clearAiConversation(kind).catch(() => {})
  }

  return { state, updateState, clearState, hydrated }
}
