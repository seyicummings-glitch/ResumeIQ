import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Send, Paperclip, ImagePlus, FileUp, X, Sparkles, FileText, Link2 } from 'lucide-react'
import clsx from 'clsx'
import { useResumes } from '../hooks/useResumes'
import * as resumeApi from '../api/resume'
import * as jdApi from '../api/jobDescription'
import { useChatAboutResume, useUploadResumeForChat, useSaveEnhancedResume } from '../hooks/useResumeBuilder'
import { useResumeBuilderDraft } from '../resume/ResumeBuilderDraftContext'
import Button, { buttonClasses } from '../components/ui/Button'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'

const URL_PATTERN = /https?:\/\/[^\s]+/i

const ATTACHMENT_ACCEPT = '.png,.jpg,.jpeg,.webp,.gif,.pdf,.docx,.txt'
const MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024

/** Reads a File as a data URL (data:<mime>;base64,<payload>) — used both for the base64 payload
 * the backend needs and, for images, directly as the local preview thumbnail's src. */
function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error("Couldn't read that file."))
    reader.readAsDataURL(file)
  })
}

function Avatar({ isAssistant }) {
  if (isAssistant) {
    return (
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white"
        style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}
        aria-hidden="true"
      >
        <Sparkles size={15} />
      </div>
    )
  }
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-border/50 text-xs font-bold text-text-h" aria-hidden="true">
      You
    </div>
  )
}

function ChatBubble({ role, content, attachment }) {
  const isAssistant = role === 'assistant'
  return (
    <div className={clsx('flex items-end gap-2.5', !isAssistant && 'flex-row-reverse')}>
      <Avatar isAssistant={isAssistant} />
      <div
        className={clsx(
          'flex max-w-[80%] flex-col gap-2 rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isAssistant ? 'rounded-bl-sm bg-surface text-text-h' : 'rounded-br-sm bg-accent text-accent-contrast'
        )}
      >
        {attachment && (
          <div
            className={clsx(
              'flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs',
              isAssistant ? 'bg-bg/60' : 'bg-black/10'
            )}
          >
            {attachment.mimeType?.startsWith('image/') ? (
              <ImagePlus size={13} className="shrink-0" aria-hidden="true" />
            ) : (
              <FileUp size={13} className="shrink-0" aria-hidden="true" />
            )}
            <span className="truncate">{attachment.filename}</span>
          </div>
        )}
        {content && <span className="whitespace-pre-wrap">{content}</span>}
      </div>
    </div>
  )
}

function TypingBubble() {
  return (
    <div className="flex items-end gap-2.5">
      <Avatar isAssistant />
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm bg-surface px-4 py-3">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-text/50"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}

function DraftPreview({ draft, sourceLabel, onSave, isSaving, isSaved }) {
  const hasContent = draft && (draft.summary || draft.experienceBullets.length > 0 || draft.skillsSection)

  return (
    <Card className="flex h-full flex-col gap-0 p-0">
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3.5">
        <h2 className="text-sm font-semibold text-text-h">Your resume draft</h2>
        {sourceLabel && (
          <Badge tone={sourceLabel === 'AI-generated' ? 'accent' : 'neutral'}>{sourceLabel}</Badge>
        )}
      </div>

      {!hasContent ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
          <FileText size={22} className="text-text/40" aria-hidden="true" />
          <p className="text-sm text-text/70">
            Nothing drafted yet — chat with the AI or attach a resume to get started.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text/70">Summary</p>
            <p className="text-sm text-text-h">{draft.summary || '(not written yet)'}</p>
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text/70">Experience</p>
            {draft.experienceBullets.length > 0 ? (
              <ul className="flex flex-col gap-1.5 text-sm text-text-h">
                {draft.experienceBullets.map((bullet, index) => (
                  <li key={index}>• {bullet}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-h">(not written yet)</p>
            )}
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text/70">Skills</p>
            <p className="text-sm text-text-h">{draft.skillsSection || '(not written yet)'}</p>
          </div>
        </div>
      )}

      <div className="border-t border-border p-3">
        <Button onClick={onSave} isLoading={isSaving} disabled={!hasContent || isSaved} className="w-full">
          {isSaved ? 'Saved' : 'Save as resume version'}
        </Button>
      </div>
    </Card>
  )
}

export default function ResumeBuilderPage() {
  const { data: resumes } = useResumes()
  const chatMutation = useChatAboutResume()
  const uploadMutation = useUploadResumeForChat()
  const saveMutation = useSaveEnhancedResume()
  const { state, updateState, hydrated } = useResumeBuilderDraft()
  const { messages, draft, jdContent, jdSourceUrl } = state

  const activeResume = resumes?.find((resume) => resume.is_active)

  const greeting = activeResume
    ? `Hi! "${activeResume.filename}" is your currently active resume. Want me to review it and suggest improvements, tell me what to change, or attach a different file to start from that instead — whatever's easiest.`
    : "Hi! Let's build your resume together — just tell me a bit about yourself (even something like \"help me build my resume\" works) and I'll ask what I need as we go. You can also attach an existing CV using the paperclip below to start from that."
  const displayMessages = messages.length === 0 ? [{ role: 'assistant', content: greeting }] : messages

  const [input, setInput] = useState('')
  const [chatError, setChatError] = useState(null)
  const [jdExtracting, setJdExtracting] = useState(false)
  const [pendingAttachment, setPendingAttachment] = useState(null)
  const [attachmentLoading, setAttachmentLoading] = useState(false)
  const scrollRef = useRef(null)
  const fileInputRef = useRef(null)
  const attachmentInputRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, chatMutation.isPending, uploadMutation.isPending, jdExtracting])

  async function sendMessage(content, jdContentOverride, attachment = null) {
    const nextMessages = [
      ...messages,
      {
        role: 'user',
        content,
        ...(attachment ? { attachment: { filename: attachment.filename, mimeType: attachment.mimeType } } : {}),
      },
    ]
    updateState({ messages: nextMessages })
    setChatError(null)

    try {
      const result = await chatMutation.mutateAsync({
        conversation: nextMessages.map(({ role, content: text }) => ({ role, content: text })),
        currentSummary: draft?.summary || '',
        currentExperienceBullets: draft?.experienceBullets || [],
        currentSkillsSection: draft?.skillsSection || '',
        jdContent: jdContentOverride ?? jdContent,
        attachment,
      })
      updateState({
        messages: [...nextMessages, { role: 'assistant', content: result.reply, source: result.source }],
        draft: {
          summary: result.summary,
          experienceBullets: result.experienceBullets,
          skillsSection: result.skillsSection,
        },
      })
      saveMutation.reset()
    } catch (err) {
      setChatError(err.message)
    }
  }

  async function handleAttachmentSelected(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    if (file.size > MAX_ATTACHMENT_BYTES) {
      setChatError('That file is too large to attach (max 8MB).')
      return
    }

    setChatError(null)
    setAttachmentLoading(true)
    try {
      const dataUrl = await readFileAsDataUrl(file)
      const base64 = dataUrl.split(',')[1] || ''
      setPendingAttachment({
        filename: file.name,
        mimeType: file.type || 'application/octet-stream',
        dataBase64: base64,
        previewUrl: file.type.startsWith('image/') ? dataUrl : null,
      })
    } catch (err) {
      setChatError(err.message)
    } finally {
      setAttachmentLoading(false)
    }
  }

  async function handleSend(event) {
    event.preventDefault()
    const text = input.trim()
    if ((!text && !pendingAttachment) || chatMutation.isPending || jdExtracting || attachmentLoading) return
    setInput('')

    if (pendingAttachment) {
      const attachment = pendingAttachment
      setPendingAttachment(null)
      await sendMessage(text, undefined, attachment)
      return
    }

    // The AI itself can't browse links, so a job posting URL needs to go
    // through the real extraction pipeline first — otherwise it just tells
    // the user it can't open links.
    const urlMatch = text.match(URL_PATTERN)
    if (urlMatch) {
      await sendJobUrl(text, urlMatch[0])
      return
    }

    await sendMessage(text)
  }

  async function sendJobUrl(originalText, url) {
    setChatError(null)
    setJdExtracting(true)
    try {
      const extracted = await jdApi.parseUrl(url)
      const extractedText = extracted.extracted_text_preview?.trim()
      if (!extractedText) {
        throw new Error("Couldn't extract any content from that job posting URL.")
      }
      updateState({ jdContent: extractedText, jdSourceUrl: url })
      await sendMessage(originalText, extractedText)
    } catch (err) {
      setChatError(
        `Couldn't extract that job posting automatically (${err.message}). Try pasting the job description text directly instead.`
      )
    } finally {
      setJdExtracting(false)
    }
  }

  async function handleFileSelected(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setChatError(null)
    try {
      await uploadMutation.mutateAsync(file)
      await sendMessage(
        `📎 Attached ${file.name} — please review it and suggest how you can help, or ask me what I'd like changed.`
      )
    } catch (err) {
      setChatError(err.message)
    }
  }

  function handleSave() {
    if (!draft) return
    saveMutation.mutate(
      {
        resumeId: activeResume?.id,
        summary: draft.summary,
        experienceBullets: draft.experienceBullets,
        skillsSection: draft.skillsSection,
      },
      {
        onSuccess: (result) => {
          updateState({
            messages: [
              ...messages,
              {
                role: 'assistant',
                content: `Saved as ${result.label || `version ${result.version}`}.`,
              },
            ],
          })
        },
        onError: (error) => setChatError(error.message),
      }
    )
  }

  const isBusy = chatMutation.isPending || uploadMutation.isPending || jdExtracting || attachmentLoading
  const lastAssistantMessage = [...messages].reverse().find((m) => m.role === 'assistant')
  const sourceLabel =
    lastAssistantMessage?.source === 'ai' ? 'AI-generated' : lastAssistantMessage?.source === 'fallback' ? 'AI unavailable' : null

  if (!hydrated) {
    return (
      <div className="flex h-[calc(100vh-9rem)] items-center justify-center py-8">
        <Spinner label="Loading your conversation…" />
      </div>
    )
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-[100rem] flex-col gap-4 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">AI Resume Builder</h1>
        <p className="mt-1 text-sm text-text">
          Chat with the AI to build a new resume or edit one you've attached — add, remove, or rewrite anything.
        </p>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="flex min-h-0 flex-col gap-3">
          {jdSourceUrl && (
            <div className="flex items-center gap-1.5 rounded-md bg-surface px-3 py-1.5 text-xs text-text/70">
              <Link2 size={12} aria-hidden="true" className="shrink-0 text-accent" />
              <span className="truncate">Tailoring to job posting: {jdSourceUrl}</span>
            </div>
          )}

          <div ref={scrollRef} className="flex flex-1 flex-col gap-4 overflow-y-auto rounded-xl border border-border bg-bg p-4">
            {displayMessages.map((message, index) => (
              <ChatBubble key={index} role={message.role} content={message.content} attachment={message.attachment} />
            ))}
            {jdExtracting && (
              <div className="flex items-center gap-2 text-xs text-text/60">
                <Link2 size={13} className="animate-pulse" aria-hidden="true" />
                Extracting the job posting from that link…
              </div>
            )}
            {(chatMutation.isPending || uploadMutation.isPending) && <TypingBubble />}
          </div>

          {chatError && <p className="text-sm text-danger">{chatError}</p>}

          {pendingAttachment && (
            <div className="flex items-center gap-2.5 rounded-lg border border-border bg-surface px-3 py-2">
              {pendingAttachment.previewUrl ? (
                <img src={pendingAttachment.previewUrl} alt="" className="h-10 w-10 shrink-0 rounded object-cover" />
              ) : (
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-bg text-text/60">
                  <FileUp size={16} aria-hidden="true" />
                </div>
              )}
              <span className="min-w-0 flex-1 truncate text-sm text-text-h">{pendingAttachment.filename}</span>
              <button
                type="button"
                onClick={() => setPendingAttachment(null)}
                aria-label="Remove attachment"
                className="shrink-0 rounded-md p-1 text-text hover:bg-border/40"
              >
                <X size={15} aria-hidden="true" />
              </button>
            </div>
          )}

          <form onSubmit={handleSend} className="flex items-end gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept={resumeApi.ALLOWED_RESUME_EXTENSIONS.join(',')}
              className="hidden"
              onChange={handleFileSelected}
            />
            <Button
              type="button"
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              isLoading={uploadMutation.isPending}
              disabled={isBusy}
              title="Attach a resume file (sets your active resume)"
            >
              <Paperclip size={15} aria-hidden="true" />
            </Button>
            <input
              ref={attachmentInputRef}
              type="file"
              accept={ATTACHMENT_ACCEPT}
              className="hidden"
              onChange={handleAttachmentSelected}
            />
            <Button
              type="button"
              variant="secondary"
              onClick={() => attachmentInputRef.current?.click()}
              isLoading={attachmentLoading}
              disabled={isBusy}
              title="Attach an image, screenshot, PDF, or document to this message"
            >
              <ImagePlus size={15} aria-hidden="true" />
            </Button>
            <textarea
              rows={2}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  handleSend(event)
                }
              }}
              placeholder={
                pendingAttachment
                  ? 'Add a message about this file (optional)…'
                  : 'Tell the AI what to build, add, remove, or change…'
              }
              disabled={isBusy}
              className="flex-1 resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-h placeholder:text-text/50 focus:border-accent focus:outline-none disabled:opacity-50"
            />
            <Button type="submit" disabled={isBusy || (!input.trim() && !pendingAttachment)} isLoading={chatMutation.isPending}>
              <Send size={15} aria-hidden="true" />
            </Button>
          </form>
        </div>

        <div className="min-h-0">
          <DraftPreview
            draft={draft}
            sourceLabel={sourceLabel}
            onSave={handleSave}
            isSaving={saveMutation.isPending}
            isSaved={saveMutation.isSuccess}
          />
        </div>
      </div>

      <p className="text-xs text-text/60">
        <Link to="/resume/versions" className={clsx(buttonClasses({ variant: 'ghost', size: 'sm' }), 'px-1 py-0 underline')}>
          View saved resume versions
        </Link>
      </p>
    </div>
  )
}
