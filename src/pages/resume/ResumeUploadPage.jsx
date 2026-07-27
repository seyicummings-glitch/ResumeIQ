import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { CircleCheckBig } from 'lucide-react'
import * as resumeApi from '../../api/resume'
import FileDropzone from '../../components/ui/FileDropzone'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Stepper from '../../components/ui/Stepper'
import ScoreGauge from '../../components/charts/ScoreGauge'
import ErrorState from '../../components/ui/ErrorState'
import Badge from '../../components/ui/Badge'
import { useToast } from '../../components/ui/Toast'
import { buttonClasses } from '../../components/ui/Button'

const STEPS = ['Upload & preview', 'ATS score', 'Save']

export default function ResumeUploadPage() {
  const [file, setFile] = useState(null)
  const [jobDescriptionText, setJobDescriptionText] = useState('')
  const { showToast } = useToast()

  const analyzeMutation = useMutation({
    mutationFn: async (selectedFile) => {
      const [uploadResult, atsResult] = await Promise.all([
        resumeApi.uploadResume(selectedFile),
        resumeApi.getAtsScore(selectedFile),
      ])
      return { uploadResult, atsResult }
    },
  })

  const suggestionsMutation = useMutation({
    mutationFn: () => resumeApi.getAiSuggestions(file, jobDescriptionText || undefined),
  })

  const saveMutation = useMutation({
    mutationFn: () => resumeApi.saveResume(file),
    onSuccess: () => showToast('Resume saved to your account.', { tone: 'success' }),
  })

  function handleFileSelected(nextFile) {
    setFile(nextFile)
    analyzeMutation.reset()
    suggestionsMutation.reset()
    saveMutation.reset()
    if (nextFile) analyzeMutation.mutate(nextFile)
  }

  const currentStep = saveMutation.isSuccess ? 2 : analyzeMutation.isSuccess ? 1 : 0
  const atsResult = analyzeMutation.data?.atsResult?.ats_result

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Upload your resume</h1>
        <p className="mt-1 text-sm text-text">PDF or Word (.docx), up to 10MB.</p>
      </div>

      <Stepper steps={STEPS} currentStep={currentStep} />

      <FileDropzone
        label="Resume file"
        hint="Accepted formats: PDF, DOCX"
        accept={resumeApi.ALLOWED_RESUME_EXTENSIONS}
        maxSizeMb={resumeApi.MAX_RESUME_FILE_SIZE_MB}
        file={file}
        onFileSelected={handleFileSelected}
      />

      {analyzeMutation.isPending && (
        <Card>
          <p className="text-sm text-text">Analyzing your resume…</p>
        </Card>
      )}

      {analyzeMutation.isError && (
        <ErrorState message={analyzeMutation.error.message} onRetry={() => analyzeMutation.mutate(file)} />
      )}

      {analyzeMutation.isSuccess && atsResult && (
        <Card className="flex flex-col gap-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:justify-between">
            <ScoreGauge score={atsResult.overall_ats_score} label="ATS score" />
            <div className="flex-1">
              <p className="text-sm text-text">
                Extracted {analyzeMutation.data.uploadResult.character_count.toLocaleString()} characters from{' '}
                {analyzeMutation.data.uploadResult.filename}.
              </p>
              {atsResult.issues.length > 0 ? (
                <ul className="mt-3 flex flex-col gap-1.5">
                  {atsResult.issues.map((issue) => (
                    <li key={issue} className="text-sm text-text-h">
                      • {issue}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-success">No issues found — this resume looks ATS-friendly.</p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => saveMutation.mutate()} isLoading={saveMutation.isPending} disabled={saveMutation.isSuccess}>
              {saveMutation.isSuccess ? (
                <>
                  <CircleCheckBig size={16} aria-hidden="true" /> Saved
                </>
              ) : (
                'Save to my resumes'
              )}
            </Button>
            {saveMutation.isSuccess && (
              <Link to="/dashboard" className={buttonClasses({ variant: 'secondary' })}>
                Go to dashboard
              </Link>
            )}
          </div>
          {saveMutation.isError && <p className="text-sm text-danger">{saveMutation.error.message}</p>}
        </Card>
      )}

      {analyzeMutation.isSuccess && (
        <Card className="flex flex-col gap-3">
          <h2 className="text-base font-semibold text-text-h">Get AI suggestions (optional)</h2>
          <label htmlFor="jd-context" className="text-sm font-medium text-text-h">
            Target job description (optional)
          </label>
          <textarea
            id="jd-context"
            rows={4}
            value={jobDescriptionText}
            onChange={(event) => setJobDescriptionText(event.target.value)}
            placeholder="Paste a job description to tailor suggestions toward it…"
            className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-h"
          />
          <Button
            variant="secondary"
            onClick={() => suggestionsMutation.mutate()}
            isLoading={suggestionsMutation.isPending}
            className="w-fit"
          >
            Get suggestions
          </Button>

          {suggestionsMutation.isError && <p className="text-sm text-danger">{suggestionsMutation.error.message}</p>}

          {suggestionsMutation.isSuccess && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Badge tone={suggestionsMutation.data.ai_suggestions.source === 'ai' ? 'accent' : 'neutral'}>
                  {suggestionsMutation.data.ai_suggestions.source === 'ai' ? 'AI-generated' : 'Rule-based fallback'}
                </Badge>
              </div>
              <p className="text-sm text-text-h">{suggestionsMutation.data.ai_suggestions.overall_assessment}</p>
              {suggestionsMutation.data.ai_suggestions.suggestions.map((suggestion, index) => (
                <div key={index} className="rounded-lg border border-border p-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-accent">{suggestion.category}</p>
                  <p className="mt-1 text-sm text-text-h">{suggestion.issue}</p>
                  <p className="mt-1 text-sm text-text">{suggestion.suggestion}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
