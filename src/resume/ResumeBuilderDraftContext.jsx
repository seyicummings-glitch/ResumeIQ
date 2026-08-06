import { createContext, useContext, useState } from 'react'

const ResumeBuilderDraftContext = createContext(null)

const initialState = {
  messages: [],
  draft: null,
  jdContent: '',
  jdSourceUrl: '',
}

/**
 * Holds the in-progress AI Resume Builder conversation (chat transcript, the
 * draft resume built so far, and any job description extracted from a link)
 * at a level above the router so it survives navigating to other pages and
 * back — it only changes when the user actively chats or explicitly clears
 * it, never on navigation.
 */
export function ResumeBuilderDraftProvider({ children }) {
  const [state, setState] = useState(initialState)

  function updateState(patch) {
    setState((current) => ({ ...current, ...patch }))
  }

  function clearState() {
    setState(initialState)
  }

  return (
    <ResumeBuilderDraftContext.Provider value={{ state, updateState, clearState }}>
      {children}
    </ResumeBuilderDraftContext.Provider>
  )
}

export function useResumeBuilderDraft() {
  const ctx = useContext(ResumeBuilderDraftContext)
  if (!ctx) throw new Error('useResumeBuilderDraft must be used within a ResumeBuilderDraftProvider')
  return ctx
}
