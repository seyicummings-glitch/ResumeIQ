import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, ListChecks, Save } from 'lucide-react'
import { useResumes } from '../hooks/useResumes'
import { useJobDescriptions } from '../hooks/useJobDescriptions'
import { useRecommendations } from '../hooks/useRecommendations'
import * as matchingApi from '../api/matching'
import { ALLOWED_RESUME_EXTENSIONS, MAX_RESUME_FILE_SIZE_MB } from '../api/resume'
import Card from '../components/ui/Card'
import Select from '../components/ui/Select'
import Button, { buttonClasses } from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import ScoreBadge from '../components/ui/ScoreBadge'
import Badge from '../components/ui/Badge'
import FileDropzone from '../components/ui/FileDropzone'
import TextArea from '../components/ui/TextArea'
import ScoreGauge from '../components/charts/ScoreGauge'
import ScoreBreakdownBars from '../components/charts/ScoreBreakdownBars'
import { useToast } from '../components/ui/Toast'

function toBreakdownItems(matchResult) {
  const items = [
    { label: 'Skills', score: matchResult.skill_match.skill_score },
    { label: 'Experience', score: matchResult.experience_match.experience_score },
    { label: 'Qualifications', score: matchResult.qualification_match.qualification_score },
  ]
  if (matchResult.github_match) items.push({ label: 'GitHub', score: matchResult.github_match.github_bonus_score })
  return items
}

function RecommendationRow({ recommendation, resumeId }) {
  const [expanded, setExpanded] = useState(false)
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  const saveMutation = useMutation({
    mutationFn: () => matchingApi.saveAnalysis({ resumeId, jobDescriptionId: recommendation.job_description_id }),
    onSuccess: () => {
      showToast('Analysis saved — check Skill Assessment, Interview Practice, and Learning Roadmap for personalized results.', { tone: 'success' })
      queryClient.invalidateQueries({ queryKey: ['analysisHistory'] })
    },
    onError: (error) => showToast(error.message, { tone: 'error' }),
  })

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-surface"
      >
        <span className="font-medium text-text-h">{recommendation.title || 'Untitled job description'}</span>
        <ScoreBadge score={recommendation.overall_match_score} />
      </button>
      {expanded && (
        <div className="flex flex-col gap-4 px-4 pb-4">
          <ScoreBreakdownBars
            items={toBreakdownItems(recommendation)}
            caption="Weighted: Skills 50% · Experience 30% · Qualifications 20% (or 45/25/15/15 with a GitHub bonus)"
          />
          <Button
            variant="secondary"
            size="sm"
            className="w-fit"
            onClick={() => saveMutation.mutate()}
            isLoading={saveMutation.isPending}
            disabled={saveMutation.isSuccess}
          >
            <Save size={14} aria-hidden="true" />
            {saveMutation.isSuccess ? 'Analysis saved' : 'Save this analysis'}
          </Button>
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const resumesQuery = useResumes()
  const jobDescriptionsQuery = useJobDescriptions()
  const [selectedResumeId, setSelectedResumeId] = useState('')

  useEffect(() => {
    if (!selectedResumeId && resumesQuery.data?.length) {
      setSelectedResumeId(String(resumesQuery.data[0].id))
    }
  }, [resumesQuery.data, selectedResumeId])

  const recommendationsQuery = useRecommendations({ resumeId: selectedResumeId ? Number(selectedResumeId) : undefined })

  const [matchFile, setMatchFile] = useState(null)
  const [matchJobDescription, setMatchJobDescription] = useState('')
  const analyzeMutation = useMutation({
    mutationFn: () => matchingApi.analyzeMatch({ file: matchFile, jobDescription: matchJobDescription }),
  })

  if (resumesQuery.isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading your dashboard…" />
      </div>
    )
  }

  if (resumesQuery.isError) {
    return <ErrorState message={resumesQuery.error.message} onRetry={resumesQuery.refetch} />
  }

  if (resumesQuery.data.length === 0) {
    return (
      <div className="py-8">
        <h1 className="mb-6 text-2xl font-semibold text-text-h">Dashboard</h1>
        <EmptyState
          icon={FileText}
          title="No resumes yet"
          description="Upload a resume to see your ATS score, match against job descriptions, and get recommendations."
          action={
            <Link to="/resume/upload" className={buttonClasses()}>
              Upload a resume
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Dashboard</h1>
        <p className="mt-1 text-sm text-text">Track how your resumes match against your saved job descriptions.</p>
      </div>

      <Select label="Resume version" value={selectedResumeId} onChange={(event) => setSelectedResumeId(event.target.value)}>
        {resumesQuery.data.map((resume) => (
          <option key={resume.id} value={resume.id}>
            {resume.filename} — {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(resume.uploaded_at))}
          </option>
        ))}
      </Select>

      <Card className="p-0">
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <ListChecks size={18} className="text-accent" aria-hidden="true" />
          <h2 className="text-base font-semibold text-text-h">Job recommendations</h2>
        </div>

        {recommendationsQuery.isLoading && (
          <div className="flex justify-center py-8">
            <Spinner label="Loading recommendations…" />
          </div>
        )}

        {recommendationsQuery.isError && (
          <div className="p-4">
            <ErrorState message={recommendationsQuery.error.message} onRetry={recommendationsQuery.refetch} />
          </div>
        )}

        {recommendationsQuery.isSuccess && recommendationsQuery.data.noResumes && (
          <div className="p-4">
            <EmptyState
              icon={FileText}
              title="No saved resumes found"
              description="Save a resume first to get job recommendations."
              action={
                <Link to="/resume/upload" className={buttonClasses()}>
                  Upload a resume
                </Link>
              }
            />
          </div>
        )}

        {recommendationsQuery.isSuccess &&
          !recommendationsQuery.data.noResumes &&
          recommendationsQuery.data.recommendations.length === 0 && (
            <div className="p-4">
              <EmptyState
                icon={ListChecks}
                title="No saved job descriptions yet"
                description={recommendationsQuery.data.message || 'Save a job description to see how well this resume matches it.'}
                action={
                  <Link to="/job-description/new" className={buttonClasses()}>
                    Add a job description
                  </Link>
                }
              />
            </div>
          )}

        {recommendationsQuery.isSuccess && recommendationsQuery.data.recommendations.length > 0 && (
          <div>
            {recommendationsQuery.data.recommendations.map((recommendation) => (
              <RecommendationRow
                key={recommendation.job_description_id}
                recommendation={recommendation}
                resumeId={Number(selectedResumeId)}
              />
            ))}
          </div>
        )}
      </Card>

      <Card className="flex flex-col gap-4">
        <h2 className="text-base font-semibold text-text-h">Quick match check</h2>
        <p className="text-sm text-text">
          Re-upload a resume file and paste a job description to see a live match score. (The backend stores parsed
          resume text, not the original file, so a fresh file is needed here — this is separate from your saved
          resumes above.)
        </p>
        <FileDropzone
          label="Resume file"
          accept={ALLOWED_RESUME_EXTENSIONS}
          maxSizeMb={MAX_RESUME_FILE_SIZE_MB}
          file={matchFile}
          onFileSelected={setMatchFile}
        />
        <TextArea
          label="Job description"
          rows={5}
          value={matchJobDescription}
          onChange={(event) => setMatchJobDescription(event.target.value)}
          placeholder={jobDescriptionsQuery.data?.[0]?.content ? 'Paste a job description…' : 'Paste a job description…'}
        />
        <Button
          onClick={() => analyzeMutation.mutate()}
          isLoading={analyzeMutation.isPending}
          disabled={!matchFile || !matchJobDescription.trim()}
          className="w-fit"
        >
          Analyze match
        </Button>

        {analyzeMutation.isError && <p className="text-sm text-danger">{analyzeMutation.error.message}</p>}

        {analyzeMutation.isSuccess && (
          <div className="flex flex-col items-center gap-6 border-t border-border pt-6 sm:flex-row sm:items-start">
            <ScoreGauge score={analyzeMutation.data.match_result.overall_match_score} label="Match score" />
            <div className="flex-1">
              <ScoreBreakdownBars
                items={toBreakdownItems(analyzeMutation.data.match_result)}
                caption="Weighted: Skills 50% · Experience 30% · Qualifications 20%"
              />
              <div className="mt-4 flex flex-wrap gap-1.5">
                {analyzeMutation.data.match_result.skill_match.matched_skills.map((skill) => (
                  <Badge key={skill} tone="success">
                    {skill}
                  </Badge>
                ))}
                {analyzeMutation.data.match_result.skill_match.missing_skills.map((skill) => (
                  <Badge key={skill} tone="danger">
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
