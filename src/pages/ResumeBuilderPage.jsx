import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, ChevronDown, ChevronUp, Upload as UploadIcon } from 'lucide-react'
import { useResumes } from '../hooks/useResumes'
import { useGenerateEnhancedResume, useSaveEnhancedResume } from '../hooks/useResumeBuilder'
import Button, { buttonClasses } from '../components/ui/Button'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'

function extractSkillsList(skillsText) {
  if (!skillsText) return []
  return skillsText
    .split(/[,\n]/)
    .map((skill) => skill.trim())
    .filter(Boolean)
}

function ComparisonSection({ title, isOpen, onToggle, original, enhanced, renderOriginal, renderEnhanced }) {
  return (
    <Card className="flex flex-col gap-0 p-0">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
        aria-expanded={isOpen}
      >
        <h2 className="text-base font-semibold text-text-h">{title}</h2>
        {isOpen ? (
          <ChevronUp size={18} className="text-text" aria-hidden="true" />
        ) : (
          <ChevronDown size={18} className="text-text" aria-hidden="true" />
        )}
      </button>
      {isOpen && (
        <div className="grid grid-cols-1 gap-4 border-t border-border px-5 pb-5 pt-4 sm:grid-cols-2">
          <div>
            <Badge tone="neutral" className="mb-2">
              Original
            </Badge>
            <div className="text-sm text-text-h">{renderOriginal ? renderOriginal(original) : original}</div>
          </div>
          <div>
            <Badge tone="accent" className="mb-2">
              AI-enhanced
            </Badge>
            <div className="text-sm text-text-h">{renderEnhanced ? renderEnhanced(enhanced) : enhanced}</div>
          </div>
        </div>
      )}
    </Card>
  )
}

export default function ResumeBuilderPage() {
  const { data: resumes, isLoading: resumesLoading, isError: resumesError, error: resumesLoadError, refetch: refetchResumes } = useResumes()
  const { showToast } = useToast()
  const generateMutation = useGenerateEnhancedResume()
  const saveMutation = useSaveEnhancedResume()
  const [expanded, setExpanded] = useState({ summary: true, experience: true, skills: true })

  function toggleSection(section) {
    setExpanded((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  function handleSave() {
    if (!generateMutation.data) return
    saveMutation.mutate(
      {
        resumeId: generateMutation.data.resumeId,
        summary: generateMutation.data.summary,
        experienceBullets: generateMutation.data.experienceBullets,
        skillsSection: generateMutation.data.skillsSection,
      },
      {
        onSuccess: (result) => {
          showToast(
            <>
              Saved as {result.label || `version ${result.version}`}.{' '}
              <Link to="/resume/versions" className="font-medium underline">
                View version history
              </Link>
            </>,
            { tone: 'success', duration: 8000 }
          )
        },
        onError: (error) => showToast(error.message, { tone: 'error' }),
      }
    )
  }

  if (resumesLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading your resumes…" />
      </div>
    )
  }

  if (resumesError) {
    return <ErrorState message={resumesLoadError.message} onRetry={refetchResumes} />
  }

  const hasResume = (resumes?.length || 0) > 0

  if (!hasResume) {
    return (
      <div className="mx-auto max-w-2xl py-8">
        <EmptyState
          icon={UploadIcon}
          title="No saved resume yet"
          description="Upload and save a resume first, then come back here to generate an AI-enhanced version."
          action={
            <Link to="/resume/upload" className={buttonClasses()}>
              Upload a resume
            </Link>
          }
        />
      </div>
    )
  }

  const sourceResume = resumes.find((resume) => resume.id === generateMutation.data?.resumeId)
  const originalSummary = sourceResume ? (sourceResume.raw_text || '').slice(0, 500).trim() || 'No summary detected.' : ''
  const originalExperience = sourceResume?.experience?.trim() || 'No experience section detected.'
  const originalSkills = sourceResume ? extractSkillsList(sourceResume.skills) : []

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">AI Resume Builder</h1>
        <p className="mt-1 text-sm text-text">
          Generate an AI-enhanced version of your most recent saved resume — a sharper summary, more quantified
          experience bullets, and a reorganized skills section.
        </p>
      </div>

      <Card className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-text-h">Ready to generate</p>
          <p className="text-sm text-text">Uses your latest saved resume as the source.</p>
        </div>
        <Button onClick={() => generateMutation.mutate()} isLoading={generateMutation.isPending}>
          <Sparkles size={16} aria-hidden="true" /> Generate AI Resume
        </Button>
      </Card>

      {generateMutation.isError && (
        <ErrorState message={generateMutation.error.message} onRetry={() => generateMutation.mutate()} />
      )}

      {generateMutation.isSuccess && (
        <>
          <div className="flex items-center gap-2">
            <Badge tone={generateMutation.data.source === 'ai' ? 'accent' : 'neutral'}>
              {generateMutation.data.source === 'ai' ? 'AI-generated' : 'Rule-based fallback'}
            </Badge>
          </div>

          {generateMutation.data.source === 'fallback' && generateMutation.data.overallAssessment && (
            <p className="text-sm text-warning">{generateMutation.data.overallAssessment}</p>
          )}

          <ComparisonSection
            title="Summary"
            isOpen={expanded.summary}
            onToggle={() => toggleSection('summary')}
            original={originalSummary}
            enhanced={generateMutation.data.summary}
          />

          <ComparisonSection
            title="Experience"
            isOpen={expanded.experience}
            onToggle={() => toggleSection('experience')}
            original={originalExperience}
            enhanced={generateMutation.data.experienceBullets}
            renderOriginal={(value) => <p className="whitespace-pre-line">{value}</p>}
            renderEnhanced={(bullets) => (
              <ul className="flex flex-col gap-1.5">
                {bullets.map((bullet, index) => (
                  <li key={index}>• {bullet}</li>
                ))}
              </ul>
            )}
          />

          <ComparisonSection
            title="Skills"
            isOpen={expanded.skills}
            onToggle={() => toggleSection('skills')}
            original={originalSkills}
            enhanced={generateMutation.data.skillsSection}
            renderOriginal={(skills) =>
              skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {skills.map((skill) => (
                    <Badge key={skill} tone="neutral">
                      {skill}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p>No skills detected.</p>
              )
            }
            renderEnhanced={(value) => <p className="whitespace-pre-line">{value}</p>}
          />

          <Card className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-text">Happy with the result? Save it as a new resume version.</p>
            <Button onClick={handleSave} isLoading={saveMutation.isPending} disabled={saveMutation.isSuccess}>
              {saveMutation.isSuccess ? 'Saved' : 'Save as new version'}
            </Button>
          </Card>
          {saveMutation.isError && <p className="text-sm text-danger">{saveMutation.error.message}</p>}
        </>
      )}
    </div>
  )
}
