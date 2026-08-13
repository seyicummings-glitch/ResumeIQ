import { useMutation } from '@tanstack/react-query'
import { generateDocument } from '../api/documents'

/** Generates and downloads a PDF report for an analysis — used by the "Download PDF report"
 * action on Analysis History and Analysis Results. */
export function useGenerateDocument() {
  return useMutation({ mutationFn: generateDocument })
}
