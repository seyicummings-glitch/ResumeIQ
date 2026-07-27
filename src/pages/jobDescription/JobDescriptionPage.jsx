import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import * as jdApi from '../../api/jobDescription'
import { useAuth } from '../../auth/AuthContext'
import { useToast } from '../../components/ui/Toast'
import { Tabs } from '../../components/ui/Tabs'
import TextArea from '../../components/ui/TextArea'
import Input from '../../components/ui/Input'
import FileDropzone from '../../components/ui/FileDropzone'
import Button, { buttonClasses } from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import ErrorState from '../../components/ui/ErrorState'
import JobDescriptionAnalysisResult from './JobDescriptionAnalysisResult'

const TABS = [
  { id: 'text', label: 'Paste text' },
  { id: 'file', label: 'Upload file' },
  { id: 'url', label: 'From URL' },
]

export default function JobDescriptionPage() {
  const { isAuthenticated } = useAuth()
  const { showToast } = useToast()

  const [activeTab, setActiveTab] = useState('text')
  const [pastedText, setPastedText] = useState('')
  const [file, setFile] = useState(null)
  const [url, setUrl] = useState('')

  const [saveTitle, setSaveTitle] = useState('')
  const [saveContent, setSaveContent] = useState('')

  const parseMutation = useMutation({
    mutationFn: async () => {
      if (activeTab === 'text') return jdApi.parseText(pastedText)
      if (activeTab === 'file') return jdApi.parseFile(file)
      return jdApi.parseUrl(url)
    },
    onSuccess: (result) => {
      setSaveContent(activeTab === 'text' ? pastedText : result.extracted_text_preview || '')
    },
  })

  const saveMutation = useMutation({
    mutationFn: () => jdApi.saveJobDescription({ title: saveTitle, content: saveContent }),
    onSuccess: () => showToast('Job description saved.', { tone: 'success' }),
  })

  function handleTabChange(tabId) {
    setActiveTab(tabId)
    parseMutation.reset()
    saveMutation.reset()
  }

  function handleAnalyze(event) {
    event.preventDefault()
    parseMutation.mutate()
  }

  const canAnalyze = activeTab === 'text' ? pastedText.trim().length > 0 : activeTab === 'file' ? Boolean(file) : url.trim().length > 0

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Add a job description</h1>
        <p className="mt-1 text-sm text-text">Paste text, upload a file, or link a posting to see required skills and experience level.</p>
      </div>

      <Card>
        <Tabs tabs={TABS} activeId={activeTab} onChange={handleTabChange}>
          <form onSubmit={handleAnalyze} className="flex flex-col gap-4">
            {activeTab === 'text' && (
              <TextArea
                label="Job description text"
                required
                rows={8}
                value={pastedText}
                onChange={(event) => setPastedText(event.target.value)}
                placeholder="Paste the full job description here…"
              />
            )}
            {activeTab === 'file' && (
              <FileDropzone
                label="Job description file"
                hint="Accepted formats: PDF, DOCX, TXT"
                accept={jdApi.ALLOWED_JD_FILE_EXTENSIONS}
                file={file}
                onFileSelected={setFile}
              />
            )}
            {activeTab === 'url' && (
              <Input
                label="Job posting URL"
                type="url"
                required
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com/careers/senior-engineer"
              />
            )}
            <Button type="submit" isLoading={parseMutation.isPending} disabled={!canAnalyze} className="w-fit">
              Analyze
            </Button>
          </form>
        </Tabs>
      </Card>

      {parseMutation.isError && (
        <ErrorState message={parseMutation.error.message} onRetry={() => parseMutation.mutate()} />
      )}

      {parseMutation.isSuccess && (
        <Card>
          <h2 className="mb-4 text-base font-semibold text-text-h">Analysis</h2>
          <JobDescriptionAnalysisResult analysis={parseMutation.data.job_description_analysis} />
        </Card>
      )}

      {parseMutation.isSuccess && (
        <Card className="flex flex-col gap-4">
          <h2 className="text-base font-semibold text-text-h">Save this job description</h2>
          {!isAuthenticated ? (
            <p className="text-sm text-text">
              <Link to="/login" className="font-medium text-accent hover:underline">
                Log in
              </Link>{' '}
              to save job descriptions to your account.
            </p>
          ) : (
            <>
              {activeTab !== 'text' && (
                <p className="rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning">
                  This is a preview of the extracted text (first 500 characters). Edit or paste the full text below before saving if you want the complete job description stored.
                </p>
              )}
              <Input label="Title (optional)" value={saveTitle} onChange={(event) => setSaveTitle(event.target.value)} />
              <TextArea
                label="Content to save"
                rows={6}
                value={saveContent}
                onChange={(event) => setSaveContent(event.target.value)}
              />
              <div className="flex items-center gap-3">
                <Button onClick={() => saveMutation.mutate()} isLoading={saveMutation.isPending} disabled={!saveContent.trim()}>
                  Save job description
                </Button>
                {saveMutation.isSuccess && (
                  <Link to="/dashboard" className={buttonClasses({ variant: 'secondary' })}>
                    Go to dashboard
                  </Link>
                )}
              </div>
              {saveMutation.isError && <p className="text-sm text-danger">{saveMutation.error.message}</p>}
            </>
          )}
        </Card>
      )}
    </div>
  )
}
