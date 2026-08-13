import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import {
  listAiConversations,
  createAiConversation,
  getAiConversationById,
  saveAiConversationById,
  deleteAiConversationById,
} from '../api/aiConversations'

const SAVE_DEBOUNCE_MS = 500

function sortByRecency(conversations) {
  return [...conversations].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
}

/**
 * ChatGPT-style conversation history for one AI feature ("kind"): a list of past conversations
 * the user can switch between, a "start new" action, and the currently active conversation's
 * state (messages + feature-specific extra state, e.g. the Resume Builder's draft) synced to the
 * server. On first load, resumes the most recently updated conversation if one exists, or starts
 * a brand new one if this account has never used the feature.
 *
 * Distinct from useServerSyncedConversation, which models a single ongoing conversation with no
 * history or switching (still used by the Career Coach).
 *
 * @param {'resume_builder'} kind
 */
export function useConversationHistory(kind) {
  const { isAuthenticated } = useAuth()
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [state, setState] = useState({ messages: [], extra: null })
  const [hydrated, setHydrated] = useState(false)
  const saveTimerRef = useRef(null)
  const activeIdRef = useRef(null)
  const conversationsRef = useRef([])

  useEffect(() => {
    activeIdRef.current = activeId
  }, [activeId])

  useEffect(() => {
    conversationsRef.current = conversations
  }, [conversations])

  useEffect(() => {
    if (!isAuthenticated) {
      setHydrated(true)
      return
    }
    let cancelled = false

    async function hydrate() {
      try {
        const list = await listAiConversations(kind)
        if (cancelled) return

        if (list.length > 0) {
          const sorted = sortByRecency(list)
          setConversations(sorted)
          const latest = await getAiConversationById(kind, sorted[0].id)
          if (cancelled) return
          setActiveId(latest.id)
          setState({ messages: latest.messages, extra: latest.extra })
        } else {
          const created = await createAiConversation(kind)
          if (cancelled) return
          setConversations([created])
          setActiveId(created.id)
          setState({ messages: [], extra: null })
        }
      } catch {
        // A transient network error just means the account's history doesn't load this time —
        // an empty, unsynced local conversation is a reasonable fallback rather than blocking.
      } finally {
        if (!cancelled) setHydrated(true)
      }
    }

    hydrate()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, kind])

  const persist = useCallback(
    (id, nextState) => {
      if (!isAuthenticated || !id) return
      clearTimeout(saveTimerRef.current)
      saveTimerRef.current = setTimeout(() => {
        saveAiConversationById(kind, id, nextState)
          .then((saved) => {
            setConversations((current) => {
              const rest = current.filter((c) => c.id !== id)
              return sortByRecency([{ id, title: saved.title, createdAt: saved.createdAt, updatedAt: saved.updatedAt }, ...rest])
            })
          })
          .catch(() => {
            // Best-effort — the local session still has the latest state either way.
          })
      }, SAVE_DEBOUNCE_MS)
    },
    [isAuthenticated, kind]
  )

  function updateState(patch) {
    setState((current) => {
      const next = { ...current, ...patch }
      persist(activeIdRef.current, next)
      return next
    })
  }

  async function startNewConversation() {
    clearTimeout(saveTimerRef.current)
    const created = await createAiConversation(kind)
    setConversations((current) => sortByRecency([created, ...current]))
    setActiveId(created.id)
    setState({ messages: [], extra: null })
    return created.id
  }

  async function switchConversation(id) {
    if (id === activeIdRef.current) return
    clearTimeout(saveTimerRef.current)
    const loaded = await getAiConversationById(kind, id)
    setActiveId(loaded.id)
    setState({ messages: loaded.messages, extra: loaded.extra })
  }

  async function deleteConversation(id) {
    await deleteAiConversationById(kind, id)
    const remaining = conversationsRef.current.filter((c) => c.id !== id)
    setConversations(remaining)
    if (id === activeIdRef.current) {
      if (remaining.length > 0) {
        await switchConversation(remaining[0].id)
      } else {
        await startNewConversation()
      }
    }
  }

  return {
    conversations,
    activeId,
    state,
    updateState,
    startNewConversation,
    switchConversation,
    deleteConversation,
    hydrated,
  }
}
