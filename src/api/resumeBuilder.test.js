import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiRequest } from './client'
import { generateEnhancedResume, chatAboutResume, saveEnhancedResume } from './resumeBuilder'

vi.mock('./client', () => ({
  apiRequest: vi.fn(),
}))

beforeEach(() => {
  apiRequest.mockReset()
})

const RAW_CONTACT = {
  full_name: 'Jordan Mitchell', email: 'jordan@example.com', phone: '555-1234',
  linkedin: 'in/jordan', location: 'Austin, TX', portfolio: 'jordanmitchell.dev',
}
const CONTACT = {
  fullName: 'Jordan Mitchell', email: 'jordan@example.com', phone: '555-1234',
  linkedin: 'in/jordan', location: 'Austin, TX', portfolio: 'jordanmitchell.dev',
}

const RAW_SKILLS = { technical: ['SEO', 'CRM'], soft: ['Negotiation'] }
const SKILLS = { technical: ['SEO', 'CRM'], soft: ['Negotiation'] }

const RAW_EXPERIENCE = [{ title: 'Marketing Manager', company: 'Acme Co.', start_date: 'Mar 2022', end_date: 'Present', bullets: ['Did a thing.'] }]
const EXPERIENCE = [{ title: 'Marketing Manager', company: 'Acme Co.', startDate: 'Mar 2022', endDate: 'Present', bullets: ['Did a thing.'] }]

const RAW_EDUCATION = [{ degree: 'BBA, Marketing', school: 'UT Austin', date: 'May 2017' }]
const EDUCATION = [{ degree: 'BBA, Marketing', school: 'UT Austin', date: 'May 2017' }]

const RAW_PROJECTS = [{ name: 'Brand Relaunch', description: 'Led a relaunch.', technologies: ['HubSpot'], bullets: ['Increased traffic by 60%.'] }]
const PROJECTS = [{ name: 'Brand Relaunch', description: 'Led a relaunch.', technologies: ['HubSpot'], bullets: ['Increased traffic by 60%.'] }]

const RAW_LANGUAGES = [{ name: 'Spanish', proficiency: 'Fluent' }]
const LANGUAGES = [{ name: 'Spanish', proficiency: 'Fluent' }]

describe('generateEnhancedResume', () => {
  it('calls POST /resume-builder/generate and maps snake_case to camelCase', async () => {
    apiRequest.mockResolvedValue({
      title: 'Marketing Professional',
      summary: 'A summary.',
      skills: RAW_SKILLS,
      experience: RAW_EXPERIENCE,
      education: RAW_EDUCATION,
      certifications: ['HubSpot Certified'],
      projects: RAW_PROJECTS,
      languages: RAW_LANGUAGES,
      references: [],
      contact: RAW_CONTACT,
      source: 'ai',
      overall_assessment: undefined,
      resume_id: 7,
    })

    const result = await generateEnhancedResume()

    expect(apiRequest).toHaveBeenCalledWith('/resume-builder/generate', { method: 'POST', auth: true })
    expect(result).toEqual({
      title: 'Marketing Professional',
      summary: 'A summary.',
      skills: SKILLS,
      experience: EXPERIENCE,
      education: EDUCATION,
      certifications: ['HubSpot Certified'],
      projects: PROJECTS,
      languages: LANGUAGES,
      references: [],
      contact: CONTACT,
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
      title: 'Marketing Professional',
      summary: 'Updated summary.',
      skills: { technical: ['Go', 'Rust'], soft: [] },
      experience: RAW_EXPERIENCE,
      education: RAW_EDUCATION,
      certifications: [],
      projects: [],
      languages: [],
      references: [],
      contact: RAW_CONTACT,
      source: 'ai',
    })

    const result = await chatAboutResume({
      conversation: [{ role: 'user', content: 'Remove the second bullet.' }],
      currentDraft: {
        title: 'Old title',
        summary: 'Old summary.',
        skills: { technical: ['Go'], soft: [] },
        experience: EXPERIENCE,
        education: EDUCATION,
        certifications: [],
        projects: [],
        languages: [],
        references: [],
      },
    })

    expect(apiRequest).toHaveBeenCalledWith('/resume-builder/chat', {
      method: 'POST',
      auth: true,
      body: {
        conversation: [{ role: 'user', content: 'Remove the second bullet.' }],
        current_title: 'Old title',
        current_summary: 'Old summary.',
        current_skills: { technical: ['Go'], soft: [] },
        current_experience: RAW_EXPERIENCE,
        current_education: RAW_EDUCATION,
        current_certifications: [],
        current_projects: [],
        current_languages: [],
        current_references: [],
        jd_content: '',
        attachment: null,
      },
    })
    expect(result).toEqual({
      reply: 'Done.',
      title: 'Marketing Professional',
      summary: 'Updated summary.',
      skills: { technical: ['Go', 'Rust'], soft: [] },
      experience: EXPERIENCE,
      education: EDUCATION,
      certifications: [],
      projects: [],
      languages: [],
      references: [],
      contact: CONTACT,
      source: 'ai',
    })
  })

  it('includes jd_content when a job description was extracted for grounding', async () => {
    apiRequest.mockResolvedValue({
      reply: 'Tailored to the job.',
      title: '',
      summary: 'Updated summary.',
      skills: { technical: ['Python'], soft: [] },
      experience: [],
      education: [],
      certifications: [],
      projects: [],
      languages: [],
      references: [],
      contact: RAW_CONTACT,
      source: 'ai',
    })

    await chatAboutResume({
      conversation: [{ role: 'user', content: 'Tailor my resume to this job.' }],
      currentDraft: { title: '', summary: '', skills: { technical: [], soft: [] }, experience: [], education: [], certifications: [], projects: [], languages: [], references: [] },
      jdContent: 'We need a Backend Engineer skilled in Python.',
    })

    const [, options] = apiRequest.mock.calls[0]
    expect(options.body.jd_content).toBe('We need a Backend Engineer skilled in Python.')
  })

  it('maps an attachment to snake_case when one is included', async () => {
    apiRequest.mockResolvedValue({
      reply: "That's a screenshot of a job posting.",
      title: '',
      summary: '',
      skills: { technical: [], soft: [] },
      experience: [],
      education: [],
      certifications: [],
      projects: [],
      languages: [],
      references: [],
      contact: RAW_CONTACT,
      source: 'ai',
    })

    await chatAboutResume({
      conversation: [{ role: 'user', content: 'what does this say?' }],
      currentDraft: { title: '', summary: '', skills: { technical: [], soft: [] }, experience: [], education: [], certifications: [], projects: [], languages: [], references: [] },
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
      title: 'Marketing Professional',
      summary: 'Summary.',
      skills: SKILLS,
      experience: EXPERIENCE,
      education: EDUCATION,
      certifications: ['HubSpot Certified'],
      projects: PROJECTS,
      languages: LANGUAGES,
      references: [],
    })

    expect(apiRequest).toHaveBeenCalledWith('/resume-builder/save', {
      method: 'POST',
      auth: true,
      body: {
        resume_id: 3,
        title: 'Marketing Professional',
        summary: 'Summary.',
        skills: RAW_SKILLS,
        experience: RAW_EXPERIENCE,
        education: RAW_EDUCATION,
        certifications: ['HubSpot Certified'],
        projects: RAW_PROJECTS,
        languages: RAW_LANGUAGES,
        references: [],
      },
    })
    expect(result).toEqual({ message: 'Saved.', resumeId: 3, version: 2, label: 'v2 (AI-enhanced)' })
  })

  it('sends resume_id as undefined when not provided (JSON.stringify drops it, so the field is absent on the wire)', async () => {
    apiRequest.mockResolvedValue({ message: 'Saved.', resume_id: 9, version: 1, label: 'v1 (AI-built)' })

    await saveEnhancedResume({
      resumeId: undefined,
      title: '',
      summary: 'Summary.',
      skills: { technical: [], soft: [] },
      experience: [],
      education: [],
      certifications: [],
      projects: [],
      languages: [],
      references: [],
    })

    const [, options] = apiRequest.mock.calls[0]
    expect(options.body.resume_id).toBeUndefined()
    // JSON.stringify drops undefined-valued keys entirely — this is what actually
    // reaches the server, matching FastAPI's optional resume_id field.
    expect(JSON.stringify(options.body)).not.toContain('resume_id')
  })
})
