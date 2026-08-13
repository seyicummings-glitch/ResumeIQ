import { useQuery } from '@tanstack/react-query'
import { getMyJobDescriptions } from '../api/jobDescription'

export function useJobDescriptions() {
  return useQuery({ queryKey: ['jobDescriptions'], queryFn: getMyJobDescriptions })
}
