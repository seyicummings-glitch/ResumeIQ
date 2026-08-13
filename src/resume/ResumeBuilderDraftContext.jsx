import { createContext, useContext } from 'react'
import { useConversationHistory } from '../hooks/useConversationHistory'

const ResumeBuilderDraftContext = createContext(null)

const EMPTY_EXTRA = { draft: null, jdContent: '', jdSourceUrl: '' }

/**
 * Holds the AI Resume Builder's conversation history (multiple conversations per account, a
 * "New Chat" action, and switching back to any past one) above the router so it survives
 * navigating to other pages — and, via useConversationHistory, survives closing the browser or
 * logging in from a different device too. Each conversation has its own chat transcript, draft
 * resume built so far, and any job description extracted from a link.
 */
export function ResumeBuilderDraftProvider({ children }) {
  const history = useConversationHistory('resume_builder')
  const extra = history.state.extra || EMPTY_EXTRA

  const state = {
    messages: history.state.messages,
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

    history.updateState({
      ...('messages' in patch ? { messages: patch.messages } : {}),
      ...(extraChanged ? { extra: nextExtra } : {}),
    })
  }

  return (
    <ResumeBuilderDraftContext.Provider
      value={{
        state,
        updateState,
        hydrated: history.hydrated,
        conversations: history.conversations,
        activeConversationId: history.activeId,
        startNewConversation: history.startNewConversation,
        switchConversation: history.switchConversation,
        deleteConversation: history.deleteConversation,
      }}
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
