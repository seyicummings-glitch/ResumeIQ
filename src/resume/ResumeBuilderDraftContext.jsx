import { createContext, useContext } from 'react'
import { useServerSyncedConversation } from '../hooks/useServerSyncedConversation'

const ResumeBuilderDraftContext = createContext(null)

const EMPTY_EXTRA = { draft: null, jdContent: '', jdSourceUrl: '' }

/**
 * Holds the AI Resume Builder conversation (chat transcript, the draft resume built so far, and
 * any job description extracted from a link) above the router so it survives navigating to
 * other pages — and, via useServerSyncedConversation, survives closing the browser or logging
 * in from a different device too. Only changes when the user actively chats or explicitly
 * clears it.
 */
export function ResumeBuilderDraftProvider({ children }) {
  const synced = useServerSyncedConversation('resume_builder')
  const extra = synced.state.extra || EMPTY_EXTRA

  const state = {
    messages: synced.state.messages,
    draft: extra.draft ?? null,
    jdContent: extra.jdContent ?? '',
    jdSourceUrl: extra.jdSourceUrl ?? '',
  }

  function updateState(patch) {
    const nextExtra = { ...extra }
    let extraChanged = false
    if ('draft' in patch) {
      nextExtra.draft = patch.draft
      extraChanged = true
    }
    if ('jdContent' in patch) {
      nextExtra.jdContent = patch.jdContent
      extraChanged = true
    }
    if ('jdSourceUrl' in patch) {
      nextExtra.jdSourceUrl = patch.jdSourceUrl
      extraChanged = true
    }

    synced.updateState({
      ...('messages' in patch ? { messages: patch.messages } : {}),
      ...(extraChanged ? { extra: nextExtra } : {}),
    })
  }

  return (
    <ResumeBuilderDraftContext.Provider
      value={{ state, updateState, clearState: synced.clearState, hydrated: synced.hydrated }}
    >
      {children}
    </ResumeBuilderDraftContext.Provider>
  )
}

export function useResumeBuilderDraft() {
  const ctx = useContext(ResumeBuilderDraftContext)
  if (!ctx) throw new Error('useResumeBuilderDraft must be used within a ResumeBuilderDraftProvider')
  return ctx
}
