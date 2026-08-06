import { useMutation, useQueryClient } from '@tanstack/react-query'
import { generateEnhancedResume, chatAboutResume, saveEnhancedResume } from '../api/resumeBuilder'
import { saveResume } from '../api/resume'

export function useGenerateEnhancedResume() {
  return useMutation({
    mutationFn: generateEnhancedResume,
  })
}

export function useChatAboutResume() {
  return useMutation({ mutationFn: chatAboutResume })
}

/** Uploads a file straight to the account as the new active resume — used by the chat's
 * attach button so "edit this" / "build from this" has something to ground on immediately. */
export function useUploadResumeForChat() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: saveResume,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
    },
  })
}

export function useSaveEnhancedResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: saveEnhancedResume,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
      queryClient.invalidateQueries({ queryKey: ['resumeVersions'] })
    },
  })
}
