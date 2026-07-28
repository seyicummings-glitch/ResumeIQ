import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getDocuments, deleteDocument, generateDocument, downloadDocument } from '../api/documents'

export function useDocuments() {
  return useQuery({ queryKey: ['documents'], queryFn: getDocuments })
}

export function useGenerateDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: generateDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
}

export function useDownloadDocument() {
  return useMutation({
    mutationFn: downloadDocument,
  })
}
