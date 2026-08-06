import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { FileDown, RefreshCw, CircleCheck, TriangleAlert, Upload as UploadIcon, Sparkles } from 'lucide-react'
import { useAnalysisHistory, useAnalysisDetail } from '../hooks/useAnalysisHistory'
import { useGenerateDocument } from '../hooks/useDocuments'
import { useResumes } from '../hooks/useResumes'
import { useGenerateEnhancedResume } from '../hooks/useResumeBuilder'
import * as matchingApi from '../api/matching'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Card from '../components/ui/Card'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import Badge from '../components/ui/Badge'
import Button, { buttonClasses } from '../components/ui/Button'
import { Tabs } from '../components/ui/Tabs'
import { useToast } from '../components/ui/Toast'

const RING_COLORS = {
  ats: '#2563eb',
  jdMatch: '#06b6d4',
  hiringReady: '#8b5cf6',
  skill: '#10b981',
  writing: '#f59e0b',
}

function bandFor(score) {
  if (score >= 75) return 'Good'
  if (score >= 50) return 'Fair'
  return 'Needs work'
}

const SCORE_DEFINITIONS = [
  {
    label: 'ATS score',
    color: RING_COLORS.ats,
    description:
      "How well an Applicant Tracking System (the software most employers use to scan resumes before a human ever sees them) can read your resume — based on file format, section headings, and contact info completeness. This is about your resume in general, not this specific job.",
  },
  {
    label: 'JD match',
    color: RING_COLORS.jdMatch,
    description:
      "How well your resume's skills, experience, and qualifications match the specific job description you provided — a weighted blend of all three, skills weighted highest.",
  },
  {
    label: 'Hiring ready',
    color: RING_COLORS.hiringReady,
    description:
      'A single composite number blending ATS score, JD match, skill score, and writing quality — a rough "how ready is this application overall" summary.',
  },
  {
    label: 'Skill score',
    color: RING_COLORS.skill,
    description: "The percentage of the job description's required skills that were found on your resume.",
  },
  {
    label: 'Writing',
    color: RING_COLORS.writing,
    description:
      'The quality of your resume\'s writing — strong action verbs, quantified achievements, concise bullet points, and avoiding weak/passive language.',
  },
]

function ScoreLegend() {
  return (
    <Card className="flex flex-col gap-2.5 p-4">
      <p className="font-mono text-xs uppercase tracking-wide text-text/70">What each score means</p>
      <dl className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {SCORE_DEFINITIONS.map(({ label, color, description }) => (
          <div key={label}>
            <dt className="text-sm font-semibold" style={{ color }}>
              {label}
            </dt>
            <dd className="mt-0.5 text-xs text-text">{description}</dd>
          </div>
        ))}
      </dl>
    </Card>
  )
}

function MetricRing({ label, score, color }) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)))
  const circumference = 2 * Math.PI * 42
  const offset = circumference * (1 - clamped / 100)

  return (
    <Card className="flex flex-col items-center gap-2 p-4">
      <span className="font-mono text-[11px] uppercase tracking-wide text-text/70">{label}</span>
      <div className="relative flex h-24 w-24 items-center justify-center">
        <svg viewBox="0 0 100 100" className="h-24 w-24 -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="var(--border)" strokeWidth="8" />
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <span className="absolute text-xl font-bold text-text-h">{clamped}</span>
      </div>
      <span className="text-xs font-semibold" style={{ color }}>
        {bandFor(clamped)}
      </span>
    </Card>
  )
}

function buildAtsChecklist(atsResult) {
  if (!atsResult) return []

  const has = (issues, text) => (issues || []).includes(text)
  const items = []

  items.push(
    has(atsResult.contact_completeness?.issues, 'No email address detected.')
      ? { pass: false, title: 'No email address detected', why: 'ATS systems extract email from body text to build the candidate record.', fix: 'Add a professional email address near the top of your resume.' }
      : { pass: true, title: 'Email address detected', why: 'ATS systems extract email from body text — contact info is accessible.' }
  )

  items.push(
    has(atsResult.contact_completeness?.issues, 'No phone number detected.')
      ? { pass: false, title: 'No phone number detected', why: 'Some ATS require a phone number to file a complete application.', fix: 'Add a phone number in your header or contact section.' }
      : { pass: true, title: 'Phone number detected', why: 'Recruiters and ATS use this as a fallback contact method.' }
  )

  items.push(
    has(atsResult.contact_completeness?.issues, 'No LinkedIn profile detected.')
      ? { pass: false, title: 'No LinkedIn profile detected', why: 'Many recruiters cross-check candidates on LinkedIn before reaching out.', fix: 'Add your LinkedIn URL to your contact section.' }
      : { pass: true, title: 'LinkedIn profile detected', why: 'A LinkedIn link gives recruiters a fast way to verify your background.' }
  )

  const skillsCount = atsResult.skills_detected?.skills_count ?? 0
  if (skillsCount === 0) {
    items.push({ pass: false, title: 'No skills detected', why: 'ATS keyword matching relies on a visible skills list.', fix: 'Add a Skills section listing your key technical and soft skills.' })
  } else if (skillsCount < 5) {
    items.push({ pass: false, title: `Only ${skillsCount} skills detected`, why: 'A thin skills list limits how many keyword matches an ATS can find.', fix: 'List more of your relevant skills, tools, and technologies.' })
  } else {
    items.push({ pass: true, title: `${skillsCount} skills detected`, why: 'Sufficient skill signal found for keyword matching.' })
  }

  items.push(
    has(atsResult.section_completeness?.issues, 'No Summary section found.')
      ? { pass: false, title: 'No professional summary found', why: 'A summary gives ATS and recruiters immediate context for your candidacy.', fix: 'Add a 2-3 sentence summary tailored to your target role.' }
      : { pass: true, title: 'Professional summary found', why: 'A summary gives ATS and recruiters immediate context for your candidacy.' }
  )

  items.push(
    has(atsResult.section_completeness?.issues, 'No Experience section found.')
      ? { pass: false, title: 'No work experience section detected', why: 'ATS may not locate your experience if a non-standard heading is used.', fix: 'Use "Work Experience" or "Professional Experience" as the section heading.' }
      : { pass: true, title: 'Work experience section detected', why: 'This is the section ATS and recruiters weigh most heavily.' }
  )

  items.push(
    has(atsResult.section_completeness?.issues, 'No Education section found.')
      ? { pass: false, title: 'No education section found', why: 'Many ATS filters check for a recognizable education section.', fix: 'Add an "Education" section, even if brief.' }
      : { pass: true, title: 'Education section detected', why: 'Confirms your qualifications meet role requirements.' }
  )

  items.push(
    has(atsResult.section_completeness?.issues, 'No Certifications section found.')
      ? { pass: false, title: 'No certifications found', why: 'For many technical roles, certs are used as ATS filters.', fix: 'Add a Certifications section even if empty — or list in-progress certifications.' }
      : { pass: true, title: 'Certifications section found', why: 'Certifications can be used as ATS filters for technical roles.' }
  )

  items.push(
    has(atsResult.section_completeness?.issues, 'No Projects section found.')
      ? { pass: false, title: 'No projects section found', why: "A projects section helps when your work history doesn't fully demonstrate your skills.", fix: 'Add a "Projects" section highlighting relevant work.' }
      : { pass: true, title: 'Projects section found', why: 'Projects strengthen your case when work history is limited.' }
  )

  const extractionScore = atsResult.text_extraction_health?.extraction_score ?? 25
  if (extractionScore === 0) {
    items.push({ pass: false, title: 'Resume text could not be extracted', why: 'Almost no text could be extracted — this file may be a scanned image or corrupted.', fix: 'Re-export as a text-based PDF or DOCX file.' })
  } else if (extractionScore <= 10) {
    items.push({ pass: false, title: 'Resume formatting may hinder parsing', why: 'Complex formatting (tables, columns, graphics) can confuse ATS parsers.', fix: 'Simplify to a single-column layout with standard section headings.' })
  } else {
    items.push({ pass: true, title: 'Resume text extracts cleanly', why: 'Clean text extraction means ATS can read your resume content reliably.' })
  }

  const extension = (atsResult.file_format_risk?.file_extension || '').replace('.', '').toUpperCase()
  const formatIssues = atsResult.file_format_risk?.issues || []
  if (formatIssues.some((issue) => issue.includes('Image file format'))) {
    items.push({ pass: false, title: 'Image file format', why: 'Most ATS systems cannot extract text from images at all.', fix: 'Submit a .docx or .pdf instead.' })
  } else if (formatIssues.some((issue) => issue.includes('.txt is parseable'))) {
    items.push({ pass: false, title: '.txt file format', why: "Plain text is parseable, but many employer portals don't accept .txt uploads.", fix: 'Submit as .pdf or .docx instead.' })
  } else {
    items.push({ pass: true, title: `Machine-readable file format (${extension})`, why: 'Text-based PDFs and DOCX files are supported by all major ATS systems.' })
  }

  return items
}

function ScoreExplanationCard({ label, score, explanation }) {
  if (!explanation) return null
  return (
    <Card className="p-3.5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-text-h">{label}</p>
        <span className="shrink-0 font-mono text-sm font-bold text-text-h">{score}%</span>
      </div>
      <p className="mt-1 text-xs text-text">
        <span className="font-mono uppercase text-text/60">Why: </span>
        {explanation}
      </p>
    </Card>
  )
}

function ScoreBreakdownSection({
  overallScore,
  overallExplanation,
  skillMatch,
  experienceMatch,
  qualificationMatch,
  hiringReadinessScore,
  hiringReadinessExplanation,
  writingResult,
}) {
  const hasAny =
    overallExplanation || skillMatch?.explanation || experienceMatch?.explanation || qualificationMatch?.explanation || hiringReadinessExplanation || writingResult

  if (!hasAny) return null

  return (
    <div className="flex flex-col gap-2.5">
      <p className="font-mono text-xs uppercase tracking-wide text-text/70">Score breakdown</p>
      <ScoreExplanationCard label="JD match" score={overallScore} explanation={overallExplanation} />
      <ScoreExplanationCard label="Skill score" score={skillMatch?.skill_score} explanation={skillMatch?.explanation} />
      <ScoreExplanationCard label="Experience match" score={experienceMatch?.experience_score} explanation={experienceMatch?.explanation} />
      <ScoreExplanationCard label="Qualification match" score={qualificationMatch?.qualification_score} explanation={qualificationMatch?.explanation} />
      <ScoreExplanationCard label="Hiring ready" score={hiringReadinessScore} explanation={hiringReadinessExplanation} />
      {writingResult && (
        <Card className="p-3.5">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-text-h">Writing</p>
            <span className="shrink-0 font-mono text-sm font-bold text-text-h">{writingResult.overall_writing_score}%</span>
          </div>
          {writingResult.issues?.length > 0 ? (
            <ul className="mt-1 flex flex-col gap-0.5 text-xs text-text">
              {writingResult.issues.map((issue) => (
                <li key={issue}>• {issue}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-xs text-text">
              No writing issues found — your bullets use strong action verbs, are quantified, concise, and avoid weak language.
            </p>
          )}
        </Card>
      )}
    </div>
  )
}

function OverviewTab({
  atsResult,
  overallScore,
  overallExplanation,
  skillMatch,
  experienceMatch,
  qualificationMatch,
  hiringReadinessScore,
  hiringReadinessExplanation,
  writingResult,
}) {
  const scoreBreakdown = (
    <ScoreBreakdownSection
      overallScore={overallScore}
      overallExplanation={overallExplanation}
      skillMatch={skillMatch}
      experienceMatch={experienceMatch}
      qualificationMatch={qualificationMatch}
      hiringReadinessScore={hiringReadinessScore}
      hiringReadinessExplanation={hiringReadinessExplanation}
      writingResult={writingResult}
    />
  )

  if (!atsResult) {
    return (
      <div className="flex flex-col gap-4">
        {scoreBreakdown}
        <Card className="flex items-center gap-3 p-4">
          <TriangleAlert size={16} className="shrink-0 text-text" aria-hidden="true" />
          <p className="text-sm text-text">
            This analysis was saved before ATS scoring was included. Save a new analysis to see the parsing checklist.
          </p>
        </Card>
      </div>
    )
  }

  const checklist = buildAtsChecklist(atsResult)

  return (
    <div className="flex flex-col gap-4">
      {scoreBreakdown}
      <div className="flex flex-col gap-2.5">
        <p className="font-mono text-xs uppercase tracking-wide text-text/70">ATS parsing check</p>
        {checklist.map((item) => (
          <Card key={item.title} className={item.pass ? 'flex items-start gap-3 border-success/25 bg-success-bg/40 p-3.5' : 'flex items-start gap-3 border-warning/25 bg-warning-bg/40 p-3.5'}>
            {item.pass ? (
              <CircleCheck size={16} className="mt-0.5 shrink-0 text-success" aria-hidden="true" />
            ) : (
              <TriangleAlert size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
            )}
            <div className="min-w-0">
              <p className="text-sm font-semibold text-text-h">{item.title}</p>
              <p className="mt-0.5 text-xs text-text">
                <span className="font-mono uppercase text-text/60">Why: </span>
                {item.why}
              </p>
              {item.fix && (
                <p className="mt-0.5 text-xs text-accent">
                  <span className="font-mono uppercase text-accent/70">Fix: </span>
                  {item.fix}
                </p>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

function KeywordsTab({ skillMatch, keywordAnalysis }) {
  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-text/70">Skills</p>
        <div className="flex flex-wrap gap-1.5">
          {skillMatch.matched_skills.map((skill) => (
            <Badge key={skill} tone="success">
              {skill}
            </Badge>
          ))}
          {skillMatch.missing_skills.map((skill) => (
            <Badge key={skill} tone="danger">
              {skill}
            </Badge>
          ))}
        </div>
      </Card>

      {keywordAnalysis ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Card className="p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-text/70">
              Keywords present ({keywordAnalysis.matched_keywords.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {keywordAnalysis.matched_keywords.map((keyword) => (
                <Badge key={keyword} tone="success">
                  {keyword}
                  {keywordAnalysis.keyword_frequency[keyword] > 1 && (
                    <span className="ml-1 opacity-70">×{keywordAnalysis.keyword_frequency[keyword]}</span>
                  )}
                </Badge>
              ))}
            </div>
          </Card>
          <Card className="p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-text/70">
              Keywords missing ({keywordAnalysis.missing_keywords.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {keywordAnalysis.missing_keywords.map((keyword) => (
                <Badge key={keyword} tone="danger">
                  {keyword}
                </Badge>
              ))}
            </div>
          </Card>
        </div>
      ) : (
        <Card className="flex items-center gap-3 p-4">
          <TriangleAlert size={16} className="shrink-0 text-text" aria-hidden="true" />
          <p className="text-sm text-text">
            This analysis was saved before keyword analysis was included. Save a new analysis to see it here.
          </p>
        </Card>
      )}
    </div>
  )
}

function SuggestionsTab({ analysisId }) {
  const suggestMutation = useMutation({
    mutationFn: () => matchingApi.getAnalysisSuggestions(analysisId),
  })

  return (
    <div className="flex flex-col gap-4">
      {!suggestMutation.isSuccess && (
        <Card className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-text-h">AI-powered resume suggestions</p>
            <p className="text-sm text-text">Tailored to this saved resume and job description.</p>
          </div>
          <Button onClick={() => suggestMutation.mutate()} isLoading={suggestMutation.isPending}>
            <Sparkles size={15} aria-hidden="true" /> Generate
          </Button>
        </Card>
      )}

      {suggestMutation.isError && (
        <ErrorState message={suggestMutation.error.message} onRetry={() => suggestMutation.mutate()} />
      )}

      {suggestMutation.isSuccess && (
        <>
          <div className="flex items-center gap-2">
            <Badge tone={suggestMutation.data.ai_suggestions.source === 'ai' ? 'accent' : 'neutral'}>
              {suggestMutation.data.ai_suggestions.source === 'ai' ? 'AI-generated' : 'Rule-based fallback'}
            </Badge>
          </div>
          <p className="text-sm text-text-h">{suggestMutation.data.ai_suggestions.overall_assessment}</p>

          {suggestMutation.data.ai_suggestions.suggestions.length === 0 ? (
            <Card className="flex items-center gap-3 p-4">
              <CircleCheck size={16} className="shrink-0 text-success" aria-hidden="true" />
              <p className="text-sm text-text-h">No major gaps found — this resume looks solid against this job description.</p>
            </Card>
          ) : (
            <div className="flex flex-col gap-3">
              {suggestMutation.data.ai_suggestions.suggestions.map((suggestion, index) => (
                <div key={index} className="rounded-lg border border-border p-3.5">
                  <p className="text-xs font-medium uppercase tracking-wide text-accent">{suggestion.category}</p>
                  <p className="mt-1 text-sm text-text-h">{suggestion.issue}</p>
                  <p className="mt-1 text-sm text-text">{suggestion.suggestion}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function BulletRewritesTab({ resumeId }) {
  const generateMutation = useGenerateEnhancedResume()

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-text-h">AI-rewritten experience bullets</p>
          <p className="text-sm text-text">Uses your latest saved resume as the source.</p>
        </div>
        <Button onClick={() => generateMutation.mutate()} isLoading={generateMutation.isPending}>
          <Sparkles size={15} aria-hidden="true" /> Generate
        </Button>
      </Card>

      {generateMutation.isError && (
        <ErrorState message={generateMutation.error.message} onRetry={() => generateMutation.mutate()} />
      )}

      {generateMutation.isSuccess && (
        <>
          {generateMutation.data.resumeId !== resumeId && (
            <p className="text-xs text-text/70">
              Generated from your current active resume, which may differ from the resume used in this analysis.
            </p>
          )}
          <Badge tone={generateMutation.data.source === 'ai' ? 'accent' : 'neutral'}>
            {generateMutation.data.source === 'ai' ? 'AI-generated' : 'Rule-based fallback'}
          </Badge>
          <Card className="p-4">
            <ul className="flex flex-col gap-2 text-sm text-text-h">
              {generateMutation.data.experienceBullets.map((bullet, index) => (
                <li key={index}>• {bullet}</li>
              ))}
            </ul>
          </Card>
          <Link to="/resume-builder" className="w-fit text-sm font-medium text-accent hover:underline">
            Open in AI Resume Builder to edit and save →
          </Link>
        </>
      )}
    </div>
  )
}

function CvPreviewTab({ resumeId }) {
  const { data: resumes, isLoading, isError, error, refetch } = useResumes()

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner label="Loading resume…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  const resume = resumes.find((row) => row.id === resumeId)

  if (!resume) {
    return (
      <Card className="flex items-center gap-3 p-4">
        <TriangleAlert size={16} className="shrink-0 text-text" aria-hidden="true" />
        <p className="text-sm text-text">This resume version is no longer available.</p>
      </Card>
    )
  }

  return (
    <Card className="p-4">
      <p className="mb-1 text-sm font-semibold text-text-h">{resume.filename}</p>
      <p className="mb-3 text-xs text-text/70">
        Uploaded {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(resume.uploaded_at))}
      </p>
      <pre className="max-h-[32rem] overflow-y-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-text-h">
        {resume.raw_text || 'No extracted text available for this resume.'}
      </pre>
    </Card>
  )
}

export default function AnalysisResultsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('overview')

  const historyQuery = useAnalysisHistory()
  const latestId = historyQuery.data?.[0]?.id
  const resolvedId = id || latestId

  const detailQuery = useAnalysisDetail(resolvedId)
  const generateDocumentMutation = useGenerateDocument()

  const reanalyzeMutation = useMutation({
    mutationFn: () => matchingApi.saveAnalysis({ resumeId: detailQuery.data.resumeId, jobDescriptionId: detailQuery.data.jobDescriptionId }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['analysisHistory'] })
      navigate(`/analysis-results/${result.analysis_id}`)
      showToast('Re-analyzed with the latest saved resume and job description.', { tone: 'success' })
    },
    onError: (error) => showToast(error.message, { tone: 'error' }),
  })

  async function handleDownloadReport() {
    try {
      await generateDocumentMutation.mutateAsync({ analysisId: detailQuery.data.id })
      showToast('PDF report generated and downloaded.', { tone: 'success' })
    } catch (downloadError) {
      showToast(downloadError.message, { tone: 'error' })
    }
  }

  if (!id && historyQuery.isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading your analyses…" />
      </div>
    )
  }

  if (!id && historyQuery.isSuccess && !latestId) {
    return (
      <div className="py-8">
        <h1 className="mb-6 text-2xl font-semibold text-text-h">Analysis Results</h1>
        <EmptyState
          icon={UploadIcon}
          title="No analyses yet"
          description="Upload your resume and paste a job description to get your ATS score, keyword match, and AI-powered suggestions."
          action={
            <Link to="/resume/upload" className={buttonClasses()}>
              Analyze my resume
            </Link>
          }
        />
      </div>
    )
  }

  if (detailQuery.isLoading || !resolvedId) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading analysis…" />
      </div>
    )
  }

  if (detailQuery.isError) {
    return <ErrorState title="Couldn't load this analysis" message={detailQuery.error.message} onRetry={detailQuery.refetch} />
  }

  const data = detailQuery.data
  const atsResult = data.atsResult
  const atsScore = atsResult?.overall_ats_score ?? 0
  const jdMatchScore = data.overallScore
  const skillScore = data.skillMatch.skill_score
  // writingResult/hiringReadinessScore come straight from the backend (writing_scorer.py /
  // readiness_scorer.py) — only fall back to an approximation for analyses saved before
  // that shipped.
  const writingScore = data.writingResult?.overall_writing_score ?? Math.round((atsScore + skillScore) / 2)
  const hiringReadyScore = data.hiringReadinessScore ?? Math.round((atsScore + jdMatchScore + skillScore) / 3)

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-h">Analysis Results</h1>
          <p className="mt-1 text-sm text-text">
            {data.resumeFilename} · {data.jobTitle} ·{' '}
            {new Intl.DateTimeFormat(undefined, { dateStyle: 'long' }).format(new Date(data.analyzedAt))}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleDownloadReport} isLoading={generateDocumentMutation.isPending}>
            <FileDown size={15} aria-hidden="true" /> PDF Report
          </Button>
          <Button
            variant="secondary"
            onClick={() => reanalyzeMutation.mutate()}
            isLoading={reanalyzeMutation.isPending}
            disabled={!data.jobDescriptionId}
          >
            <RefreshCw size={15} aria-hidden="true" /> Re-analyze
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <MetricRing label="ATS score" score={atsScore} color={RING_COLORS.ats} />
        <MetricRing label="JD match" score={jdMatchScore} color={RING_COLORS.jdMatch} />
        <MetricRing label="Hiring ready" score={hiringReadyScore} color={RING_COLORS.hiringReady} />
        <MetricRing label="Skill score" score={skillScore} color={RING_COLORS.skill} />
        <MetricRing label="Writing" score={writingScore} color={RING_COLORS.writing} />
      </div>

      <ScoreLegend />

      <Tabs
        tabs={[
          { id: 'overview', label: 'Overview' },
          { id: 'keywords', label: 'Keywords' },
          { id: 'suggestions', label: 'Suggestions' },
          { id: 'bullets', label: 'Bullet Rewrites' },
          { id: 'preview', label: 'CV Preview' },
        ]}
        activeId={activeTab}
        onChange={setActiveTab}
      >
        {activeTab === 'overview' && (
          <OverviewTab
            atsResult={atsResult}
            overallScore={jdMatchScore}
            overallExplanation={data.overallExplanation}
            skillMatch={data.skillMatch}
            experienceMatch={data.experienceMatch}
            qualificationMatch={data.qualificationMatch}
            hiringReadinessScore={hiringReadyScore}
            hiringReadinessExplanation={data.hiringReadinessExplanation}
            writingResult={data.writingResult}
          />
        )}
        {activeTab === 'keywords' && <KeywordsTab skillMatch={data.skillMatch} keywordAnalysis={data.keywordAnalysis} />}
        {activeTab === 'suggestions' && <SuggestionsTab analysisId={data.id} />}
        {activeTab === 'bullets' && <BulletRewritesTab resumeId={data.resumeId} />}
        {activeTab === 'preview' && <CvPreviewTab resumeId={data.resumeId} />}
      </Tabs>
    </div>
  )
}
