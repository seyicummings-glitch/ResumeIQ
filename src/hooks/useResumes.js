import { useQuery } from '@tanstack/react-query'
import { getMyResumes } from '../api/resume'

export function useResumes() {
  return useQuery({
    queryKey: ['resumes'],
    queryFn: async () => {
      const resumes = await getMyResumes()
      return [...resumes].sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at))
    },
  })
}
