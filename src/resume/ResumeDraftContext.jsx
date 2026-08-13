import { createContext, useContext, useState } from 'react'

const ResumeDraftContext = createContext(null)

const initialDraft = {
  file: null,
  jdTab: 'text',
  jobDescription: '',
  jdFile: null,
  jdUrl: '',
  experienceLevel: 'mid',
  githubUsername: null,
}

/**
 * Holds the in-progress Analyze Resume draft (uploaded CV, job description, etc.) at a
 * level above the router so it survives navigating to other pages and back — it only
 * changes when the user actively edits it (or explicitly clears it), never on navigation.
 */
export function ResumeDraftProvider({ children }) {
  const [draft, setDraft] = useState(initialDraft)

  function updateDraft(patch) {
    setDraft((current) => ({ ...current, ...patch }))
  }

  function clearDraft() {
    setDraft(initialDraft)
  }

  return <ResumeDraftContext.Provider value={{ draft, updateDraft, clearDraft }}>{children}</ResumeDraftContext.Provider>
}

export function useResumeDraft() {
  const ctx = useContext(ResumeDraftContext)
  if (!ctx) throw new Error('useResumeDraft must be used within a ResumeDraftProvider')
  return ctx
}
