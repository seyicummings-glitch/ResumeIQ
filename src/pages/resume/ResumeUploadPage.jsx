import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import clsx from 'clsx'
import { GitBranch, Sparkles, FileText, Link2, FileUp } from 'lucide-react'
import * as resumeApi from '../../api/resume'
import * as jdApi from '../../api/jobDescription'
import * as matchingApi from '../../api/matching'
import { useAuth } from '../../auth/AuthContext'
import { useResumeDraft } from '../../resume/ResumeDraftContext'
import FileDropzone from '../../components/ui/FileDropzone'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import TextArea from '../../components/ui/TextArea'
import Input from '../../components/ui/Input'
import Modal from '../../components/ui/Modal'
import ErrorState from '../../components/ui/ErrorState'
import { useToast } from '../../components/ui/Toast'

const JD_MODES = [
  { id: 'text', icon: FileText, title: 'Paste text' },
  { id: 'url', icon: Link2, title: 'Job URL' },
  { id: 'file', icon: FileUp, title: 'Upload file' },
]

const EXPERIENCE_LEVELS = [
  { id: 'entry', label: 'Entry', sub: '0-2 yrs' },
  { id: 'mid', label: 'Mid', sub: '3-5 yrs' },
  { id: 'senior', label: 'Senior', sub: '6-10 yrs' },
  { id: 'exec', label: 'Exec', sub: '10+ yrs' },
]

function SectionLabel({ children }) {
  return <p className="mb-1.5 font-mono text-xs uppercase tracking-wide text-text/70">{children}</p>
}

const STAGE_LABELS = {
  saving: 'Saving your resume…',
  matching: 'Running the real matching engine…',
  done: 'Done!',
}

export default function ResumeUploadPage() {
  const { isAuthenticated } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const { draft, updateDraft } = useResumeDraft()
  const { file, jdTab, jobDescription, jdFile, jdUrl, experienceLevel, githubUsername } = draft
  const [stage, setStage] = useState('idle')
  const [resolvingTitle, setResolvingTitle] = useState(false)
  const [showTitleModal, setShowTitleModal] = useState(false)
  const [manualTitle, setManualTitle] = useState('')
  const [resolvedTitle, setResolvedTitle] = useState('')

  const jdExtractMutation = useMutation({
    mutationFn: (overrideFile) => (jdTab === 'file' ? jdApi.parseFile(overrideFile ?? jdFile) : jdApi.parseUrl(jdUrl)),
    onSuccess: (result) => updateDraft({ jobDescription: result.extracted_text_preview || '' }),
  })

  function handleJdTabChange(tabId) {
    updateDraft({ jdTab: tabId })
    jdExtractMutation.reset()
  }

  function handleJdFileSelected(nextFile) {
    updateDraft({ jdFile: nextFile })
    jdExtractMutation.reset()
    if (nextFile) jdExtractMutation.mutate(nextFile)
  }

  const analyzeMutation = useMutation({
    mutationFn: async (jobTitle) => {
      setStage('saving')
      const atsResponse = await resumeApi.getAtsScore(file)
      const detectedGithub = atsResponse.contact_info?.github || null
      updateDraft({ githubUsername: detectedGithub })

      const savedResume = await resumeApi.saveResume(file)
      const savedJd = await jdApi.saveJobDescription({ title: jobTitle || undefined, content: jobDescription })

      setStage('matching')
      const savedAnalysis = await matchingApi.saveAnalysis({
        resumeId: savedResume.resume_id,
        jobDescriptionId: savedJd.id,
      })

      setStage('done')
      return savedAnalysis
    },
    onSuccess: (savedAnalysis) => {
      showToast('Analysis complete.', { tone: 'success' })
      navigate(`/analysis-results/${savedAnalysis.analysis_id}`)
    },
    onError: () => setStage('idle'),
  })

  function handleFileSelected(nextFile) {
    updateDraft({ file: nextFile })
    analyzeMutation.reset()
    setStage('idle')
  }

  /**
   * Resolves a job title before saving: reuses the title the AI already extracted while
   * parsing the file/URL (jdExtractMutation), or — for pasted text, which is never run
   * through an extraction call otherwise — parses the current text fresh. If neither finds
   * a real title, the user is prompted to type one rather than silently saving an
   * "Untitled job description".
   */
  async function handleAnalyzeClick() {
    setResolvingTitle(true)
    try {
      let title = ''
      if ((jdTab === 'file' || jdTab === 'url') && jdExtractMutation.isSuccess) {
        title = jdExtractMutation.data?.job_description_analysis?.title || ''
      }
      if (!title) {
        const parsed = await jdApi.parseText(jobDescription)
        title = parsed.job_description_analysis?.title || ''
      }

      if (title) {
        setResolvedTitle(title)
        analyzeMutation.mutate(title)
      } else {
        setManualTitle('')
        setShowTitleModal(true)
      }
    } catch {
      // Title extraction failing shouldn't block analysis — fall back to asking the user.
      setManualTitle('')
      setShowTitleModal(true)
    } finally {
      setResolvingTitle(false)
    }
  }

  function handleManualTitleSubmit(event) {
    event.preventDefault()
    const finalTitle = manualTitle.trim()
    setResolvedTitle(finalTitle)
    setShowTitleModal(false)
    analyzeMutation.mutate(finalTitle)
  }

  const isAnalyzing = analyzeMutation.isPending || resolvingTitle
  const canAnalyze = Boolean(file) && jobDescription.trim().length > 0 && isAuthenticated && !isAnalyzing

  const wordCount = jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0
  const jdWasAiExtracted = jdExtractMutation.isSuccess && jdExtractMutation.data.source === 'ai'

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Analyze Resume</h1>
        <p className="mt-1 text-sm text-text">
          Upload your resume and a job description — we'll run the real match analysis and take you straight to
          your results.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-3">
          <div>
            <SectionLabel>Resume file</SectionLabel>
            <FileDropzone
              accept={resumeApi.ALLOWED_RESUME_EXTENSIONS}
              maxSizeMb={resumeApi.MAX_RESUME_FILE_SIZE_MB}
              file={file}
              onFileSelected={handleFileSelected}
              emptyTitle="Drop resume here"
              emptySubtitle="PDF · DOCX · TXT · max 10 MB"
            />
          </div>

          <Card className="flex items-start gap-3 border-success/30 bg-success-bg p-3">
            <GitBranch size={16} className="mt-0.5 shrink-0 text-success" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-success">
                {githubUsername ? `GitHub auto-detected: @${githubUsername}` : 'GitHub auto-detected from resume'}
              </p>
              <p className="text-xs text-success/80">
                We'll automatically find and analyze your public repos from the GitHub URL in your resume.
              </p>
            </div>
          </Card>
        </div>

        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <SectionLabel>Job description</SectionLabel>
            <div className="flex gap-1 rounded-md bg-surface p-0.5">
              {JD_MODES.map(({ id, icon: Icon, title }) => (
                <button
                  key={id}
                  type="button"
                  title={title}
                  onClick={() => handleJdTabChange(id)}
                  className={clsx(
                    'flex h-7 w-7 items-center justify-center rounded transition-colors',
                    jdTab === id ? 'bg-accent/20 text-accent' : 'text-text/60 hover:text-text-h'
                  )}
                >
                  <Icon size={13} aria-hidden="true" />
                </button>
              ))}
            </div>
          </div>

          {jdTab === 'file' && (
            <div className="mb-3 flex flex-col gap-3">
              <FileDropzone
                accept={jdApi.ALLOWED_JD_FILE_EXTENSIONS}
                file={jdFile}
                onFileSelected={handleJdFileSelected}
                emptyTitle="Upload JD document"
                emptySubtitle="TXT · PDF · DOCX"
              />
              {jdExtractMutation.isPending && <p className="text-sm text-text/70">Extracting the job description…</p>}
              {jdExtractMutation.isError && <p className="text-sm text-danger">{jdExtractMutation.error.message}</p>}
            </div>
          )}

          {jdTab === 'url' && (
            <div className="mb-3 flex flex-col gap-3">
              <Input
                label="Job posting URL"
                type="url"
                value={jdUrl}
                onChange={(event) => updateDraft({ jdUrl: event.target.value })}
                placeholder="https://example.com/careers/senior-engineer"
              />
              <Button
                variant="secondary"
                size="sm"
                className="w-fit"
                onClick={() => jdExtractMutation.mutate()}
                isLoading={jdExtractMutation.isPending}
                disabled={!jdUrl.trim()}
              >
                Extract job description from URL
              </Button>
              {jdExtractMutation.isError && <p className="text-sm text-danger">{jdExtractMutation.error.message}</p>}
            </div>
          )}

          {jdExtractMutation.isSuccess && jdTab !== 'text' && (
            <p
              className={clsx(
                'mb-3 rounded-lg px-3 py-2 text-xs',
                jdWasAiExtracted ? 'bg-success-bg text-success' : 'bg-warning-bg text-warning'
              )}
            >
              {jdWasAiExtracted
                ? 'Extracted the job posting content below — review it, then analyze.'
                : "Extracted the raw page text below — AI cleanup wasn't available, so review and trim it before analyzing."}
            </p>
          )}

          <TextArea
            rows={7}
            value={jobDescription}
            onChange={(event) => updateDraft({ jobDescription: event.target.value })}
            placeholder="Paste the full job description here — required skills, qualifications, responsibilities…"
          />
          <p className="mt-1.5 font-mono text-xs text-text/60">
            {wordCount} word{wordCount === 1 ? '' : 's'} · Richer JDs yield better keyword analysis
          </p>
        </div>
      </div>

      <div>
        <SectionLabel>Experience level</SectionLabel>
        <div className="grid grid-cols-4 gap-2">
          {EXPERIENCE_LEVELS.map(({ id, label, sub }) => (
            <button
              key={id}
              type="button"
              onClick={() => updateDraft({ experienceLevel: id })}
              className={clsx(
                'rounded-md border px-2 py-2 text-center transition-colors',
                experienceLevel === id ? 'border-accent bg-accent/10 text-accent' : 'border-border text-text hover:bg-surface'
              )}
            >
              <div className="text-xs font-semibold">{label}</div>
              <div className="font-mono text-[10px] opacity-70">{sub}</div>
            </button>
          ))}
        </div>
      </div>

      {isAnalyzing ? (
        <Card className="flex flex-col gap-2 p-4">
          <div className="flex items-center gap-2 font-mono text-sm text-accent">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            {resolvingTitle ? 'Detecting the job title…' : STAGE_LABELS[stage] || STAGE_LABELS.saving}
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-border">
            <div
              className="h-full rounded-full bg-accent transition-all duration-500"
              style={{ width: resolvingTitle ? '10%' : stage === 'done' ? '100%' : stage === 'matching' ? '65%' : '25%' }}
            />
          </div>
        </Card>
      ) : (
        <div>
          <Button onClick={handleAnalyzeClick} disabled={!canAnalyze}>
            <Sparkles size={15} aria-hidden="true" /> Analyze Resume
          </Button>
          {!isAuthenticated && (
            <p className="mt-2 text-xs text-text/70">
              <Link to="/login" className="font-medium text-accent hover:underline">
                Log in
              </Link>{' '}
              to analyze and save your resume.
            </p>
          )}
          {isAuthenticated && !file && <p className="mt-2 text-xs text-text/70">Upload a resume file to get started.</p>}
          {isAuthenticated && file && !jobDescription.trim() && (
            <p className="mt-2 text-xs text-text/70">Add a job description to analyze against.</p>
          )}
        </div>
      )}

      {analyzeMutation.isError && (
        <ErrorState message={analyzeMutation.error.message} onRetry={() => analyzeMutation.mutate(resolvedTitle)} />
      )}

      <Modal isOpen={showTitleModal} onClose={() => setShowTitleModal(false)} title="What's this job called?">
        <form onSubmit={handleManualTitleSubmit} className="flex flex-col gap-4">
          <p className="text-sm text-text">
            We couldn't automatically detect a job title from this posting — enter one so it's easy to find later.
          </p>
          <Input
            label="Job title"
            autoFocus
            value={manualTitle}
            onChange={(event) => setManualTitle(event.target.value)}
            placeholder="e.g. Backend Developer"
            required
          />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setShowTitleModal(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!manualTitle.trim()}>
              Continue
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
