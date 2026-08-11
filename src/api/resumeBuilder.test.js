import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiRequest } from './client'
import { generateEnhancedResume, chatAboutResume, saveEnhancedResume } from './resumeBuilder'

vi.mock('./client', () => ({
  apiRequest: vi.fn(),
}))

beforeEach(() => {
  apiRequest.mockReset()
})

describe('generateEnhancedResume', () => {
  it('calls POST /resume-builder/generate and maps snake_case to camelCase', async () => {
    apiRequest.mockResolvedValue({
      summary: 'A summary.',
      experience_bullets: ['Did a thing.'],
      skills_section: 'Python, SQL',
      source: 'ai',
      overall_assessment: undefined,
      resume_id: 7,
    })

    const result = await generateEnhancedResume()

    expect(apiRequest).toHaveBeenCalledWith('/resume-builder/generate', { method: 'POST', auth: true })
    expect(result).toEqual({
      summary: 'A summary.',
      experienceBullets: ['Did a thing.'],
      skillsSection: 'Python, SQL',
      source: 'ai',
      overallAssessment: undefined,
      resumeId: 7,
    })
  })
})

describe('chatAboutResume', () => {
  it('sends the conversation and current draft in snake_case, and maps the reply back', async () => {
    apiRequest.mockResolvedValue({
      reply: 'Done.',
      summary: 'Updated summary.',
      experience_bullets: ['One bullet.'],
      skills_section: 'Go, Rust',
      source: 'ai',
    })

    const result = await chatAboutResume({
      conversation: [{ role: 'user', content: 'Remove the second bullet.' }],
      currentSummary: 'Old summary.',
      currentExperienceBullets: ['One bullet.', 'Two bullet.'],
      currentSkillsSection: 'Go',
    })

    expect(apiRequest).toHaveBeenCalledWith('/resume-builder/chat', {
      method: 'POST',
      auth: true,
      body: {
        conversation: [{ role: 'user', content: 'Remove the second bullet.' }],
        current_summary: 'Old summary.',
        current_experience_bullets: ['One bullet.', 'Two bullet.'],
        current_skills_section: 'Go',
        jd_content: '',
        attachment: null,
      },
    })
    expect(result).toEqual({
      reply: 'Done.',
      summary: 'Updated summary.',
      experienceBullets: ['One bullet.'],
      skillsSection: 'Go, Rust',
      source: 'ai',
    })
  })

  it('includes jd_content when a job description was extracted for grounding', async () => {
    apiRequest.mockResolvedValue({
      reply: 'Tailored to the job.',
      summary: 'Updated summary.',
      experience_bullets: [],
      skills_section: 'Python',
      source: 'ai',
    })

    await chatAboutResume({
      conversation: [{ role: 'user', content: 'Tailor my resume to this job.' }],
      currentSummary: '',
      currentExperienceBullets: [],
      currentSkillsSection: '',
      jdContent: 'We need a Backend Engineer skilled in Python.',
    })

    const [, options] = apiRequest.mock.calls[0]
    expect(options.body.jd_content).toBe('We need a Backend Engineer skilled in Python.')
  })

  it('maps an attachment to snake_case when one is included', async () => {
    apiRequest.mockResolvedValue({
      reply: "That's a screenshot of a job posting.",
      summary: '',
      experience_bullets: [],
      skills_section: '',
      source: 'ai',
    })

    await chatAboutResume({
      conversation: [{ role: 'user', content: 'what does this say?' }],
      currentSummary: '',
      currentExperienceBullets: [],
      currentSkillsSection: '',
      attachment: { filename: 'job-posting.png', mimeType: 'image/png', dataBase64: 'aGVsbG8=' },
    })

    const [, options] = apiRequest.mock.calls[0]
    expect(options.body.attachment).toEqual({
      filename: 'job-posting.png',
      mime_type: 'image/png',
      data_base64: 'aGVsbG8=',
    })
  })
})

describe('saveEnhancedResume', () => {
  it('includes resume_id when provided', async () => {
    apiRequest.mockResolvedValue({ message: 'Saved.', resume_id: 3, version: 2, label: 'v2 (AI-enhanced)' })

    const result = await saveEnhancedResume({
      resumeId: 3,
      summary: 'Summary.',
      experienceBullets: ['Bullet.'],
      skillsSection: 'Python',
    })

    expect(apiRequest).toHaveBeenCalledWith('/resume-builder/save', {
      method: 'POST',
      auth: true,
      body: {
        resume_id: 3,
        summary: 'Summary.',
        experience_bullets: ['Bullet.'],
        skills_section: 'Python',
      },
    })
    expect(result).toEqual({ message: 'Saved.', resumeId: 3, version: 2, label: 'v2 (AI-enhanced)' })
  })

  it('sends resume_id as undefined when not provided (JSON.stringify drops it, so the field is absent on the wire)', async () => {
    apiRequest.mockResolvedValue({ message: 'Saved.', resume_id: 9, version: 1, label: 'v1 (AI-built)' })

    await saveEnhancedResume({
      resumeId: undefined,
      summary: 'Summary.',
      experienceBullets: [],
      skillsSection: '',
    })

    const [, options] = apiRequest.mock.calls[0]
    expect(options.body.resume_id).toBeUndefined()
    // JSON.stringify drops undefined-valued keys entirely — this is what actually
    // reaches the server, matching FastAPI's optional resume_id field.
    expect(JSON.stringify(options.body)).not.toContain('resume_id')
  })
})
