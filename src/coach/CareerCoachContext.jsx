import { createContext, useContext, useState } from 'react'
import { useServerSyncedConversation } from '../hooks/useServerSyncedConversation'

const CareerCoachContext = createContext(null)

/**
 * Holds the Career Coach's conversation above the router (mounted in main.jsx) so it survives
 * navigating between pages — and, via useServerSyncedConversation, survives closing the browser
 * or logging in from a different device too, the same as the AI Resume Builder. Only `messages`
 * and the focused `topic` are persisted to the account; `open` (is the widget currently
 * expanded) and `error` (a transient failure message) are deliberately local-only UI state —
 * there's no reason those should follow you to another device.
 */
export function CareerCoachProvider({ children }) {
  const synced = useServerSyncedConversation('career_coach')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState(null)

  const topic = synced.state.extra?.topic ?? null

  const state = {
    open,
    messages: synced.state.messages,
    topic,
    error,
  }

  function updateState(patch) {
    if ('messages' in patch) {
      synced.updateState({ messages: patch.messages })
    }
    if ('topic' in patch) {
      synced.updateState({ extra: { ...(synced.state.extra || {}), topic: patch.topic } })
    }
    if ('error' in patch) {
      setError(patch.error)
    }
    if ('open' in patch) {
      setOpen(patch.open)
    }
  }

  function openCoach(newTopic = null) {
    setOpen(true)
    if (newTopic) {
      synced.updateState({ extra: { ...(synced.state.extra || {}), topic: newTopic } })
    }
  }

  function closeCoach() {
    setOpen(false)
  }

  function clearConversation() {
    synced.clearState()
    setError(null)
  }

  return (
    <CareerCoachContext.Provider
      value={{ state, updateState, openCoach, closeCoach, clearConversation, hydrated: synced.hydrated }}
    >
      {children}
    </CareerCoachContext.Provider>
  )
}

export function useCareerCoachContext() {
  const ctx = useContext(CareerCoachContext)
  if (!ctx) throw new Error('useCareerCoachContext must be used within a CareerCoachProvider')
  return ctx
}
