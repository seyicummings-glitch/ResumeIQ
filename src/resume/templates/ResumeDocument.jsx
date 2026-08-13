/**
 * Renders a structured resume draft as an actual document layout — the same data, four
 * different professional templates, switchable instantly with no regeneration. Deliberately
 * rendered as a fixed light "paper" page (not the app's dark/light theme) since this is meant
 * to look like something you'd print or send to a recruiter, not app chrome.
 */
export const RESUME_TEMPLATES = [
  { id: 'professional', name: 'Professional', description: 'Classic single-column layout, ATS-safe.' },
  { id: 'modern', name: 'Modern', description: 'Two-column layout with a dark sidebar.' },
  { id: 'executive', name: 'Executive', description: 'Elegant serif headings, generous spacing.' },
  { id: 'minimalist', name: 'Minimalist', description: 'Understated, plenty of white space.' },
]

const THEME = {
  professional: { accent: '#2563eb', headingFont: 'inherit' },
  modern: { accent: '#0f766e', sidebarBg: '#111827', sidebarText: '#e2e8f0', sidebarMuted: '#94a3b8', headingFont: 'inherit' },
  executive: { accent: '#92622d', headingFont: "'Georgia', 'Cambria', 'Times New Roman', serif" },
  minimalist: { accent: '#111827', headingFont: 'inherit' },
}

function joinTruthy(parts, sep) {
  return parts.filter(Boolean).join(sep)
}

function dateRange(item) {
  return joinTruthy([item.startDate, item.endDate], ' – ')
}

export function hasResumeContent(draft) {
  return Boolean(
    draft &&
      (draft.summary ||
        draft.skills?.technical?.length > 0 ||
        draft.skills?.soft?.length > 0 ||
        draft.experience?.length > 0 ||
        draft.education?.length > 0 ||
        draft.certifications?.length > 0 ||
        draft.projects?.length > 0 ||
        draft.languages?.length > 0 ||
        draft.references?.length > 0)
  )
}

function SkillGroup({ label, skills, accent }) {
  if (!skills?.length) return null
  return (
    <div>
      <p className="mb-1 text-[11px] font-bold uppercase tracking-wide" style={{ color: accent }}>
        {label}
      </p>
      <ul className="flex flex-col gap-0.5 text-[13px] leading-snug text-gray-800">
        {skills.map((skill, index) => (
          <li key={index} className="pl-3 -indent-3">
            • {skill}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ExperienceEntry({ job, accent }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[13.5px] font-bold text-gray-900">{job.title || '(untitled role)'}</p>
        {dateRange(job) && <p className="shrink-0 text-[11.5px] text-gray-500">{dateRange(job)}</p>}
      </div>
      {job.company && (
        <p className="text-[12.5px] font-medium" style={{ color: accent }}>
          {job.company}
        </p>
      )}
      {job.bullets?.length > 0 && (
        <ul className="mt-1 flex flex-col gap-0.5 text-[12.5px] leading-relaxed text-gray-700">
          {job.bullets.map((bullet, index) => (
            <li key={index} className="pl-3.5 -indent-3.5">
              • {bullet}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ProjectEntry({ project }) {
  return (
    <div>
      <p className="text-[13px] font-bold text-gray-900">{project.name}</p>
      {project.description && <p className="text-[12.5px] text-gray-700">{project.description}</p>}
      {project.technologies?.length > 0 && (
        <p className="text-[11.5px] italic text-gray-500">Technologies: {project.technologies.join(', ')}</p>
      )}
      {project.bullets?.length > 0 && (
        <ul className="mt-1 flex flex-col gap-0.5 text-[12.5px] leading-relaxed text-gray-700">
          {project.bullets.map((bullet, index) => (
            <li key={index} className="pl-3.5 -indent-3.5">
              • {bullet}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function EducationEntry({ edu }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <p className="text-[13px] text-gray-800">
        <span className="font-bold text-gray-900">{edu.degree}</span>
        {edu.school ? `, ${edu.school}` : ''}
      </p>
      {edu.date && <p className="shrink-0 text-[11.5px] text-gray-500">{edu.date}</p>}
    </div>
  )
}

/** Section heading whose visual weight changes per template — an underlined accent bar for
 * Professional/Modern, a centered serif label with a thin double rule for Executive, and a
 * quiet small-caps label with no rule at all for Minimalist. */
function Heading({ template, accent, children }) {
  if (template === 'executive') {
    return (
      <p
        className="mb-2 text-center text-[12px] font-bold uppercase tracking-[0.2em]"
        style={{ color: accent, fontFamily: THEME.executive.headingFont }}
      >
        {children}
      </p>
    )
  }
  if (template === 'minimalist') {
    return (
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.15em] text-gray-400">{children}</p>
    )
  }
  return (
    <p
      className="mb-2 border-b-2 pb-1 text-[12px] font-bold uppercase tracking-wide text-gray-900"
      style={{ borderColor: accent }}
    >
      {children}
    </p>
  )
}

function ContactLine({ contact, className = '' }) {
  const line = joinTruthy([contact?.email, contact?.phone, contact?.location, contact?.linkedin, contact?.portfolio], '   |   ')
  if (!line) return null
  return <p className={`text-[11.5px] ${className}`}>{line}</p>
}

function MainSections({ draft, template, accent }) {
  return (
    <>
      {draft.summary && (
        <section>
          <Heading template={template} accent={accent}>
            Professional Summary
          </Heading>
          <p className="text-[13px] leading-relaxed text-gray-800">{draft.summary}</p>
        </section>
      )}

      {draft.experience?.length > 0 && (
        <section>
          <Heading template={template} accent={accent}>
            Professional Experience
          </Heading>
          <div className="flex flex-col gap-3">
            {draft.experience.map((job, index) => (
              <ExperienceEntry key={index} job={job} accent={accent} />
            ))}
          </div>
        </section>
      )}

      {draft.education?.length > 0 && (
        <section>
          <Heading template={template} accent={accent}>
            Education
          </Heading>
          <div className="flex flex-col gap-1.5">
            {draft.education.map((edu, index) => (
              <EducationEntry key={index} edu={edu} />
            ))}
          </div>
        </section>
      )}

      {draft.projects?.length > 0 && (
        <section>
          <Heading template={template} accent={accent}>
            Projects
          </Heading>
          <div className="flex flex-col gap-2.5">
            {draft.projects.map((project, index) => (
              <ProjectEntry key={index} project={project} />
            ))}
          </div>
        </section>
      )}

      {draft.certifications?.length > 0 && (
        <section>
          <Heading template={template} accent={accent}>
            Certifications
          </Heading>
          <ul className="flex flex-col gap-0.5 text-[12.5px] text-gray-800">
            {draft.certifications.map((cert, index) => (
              <li key={index} className="pl-3.5 -indent-3.5">
                • {cert}
              </li>
            ))}
          </ul>
        </section>
      )}

      {draft.references?.length > 0 && (
        <section>
          <Heading template={template} accent={accent}>
            References
          </Heading>
          <ul className="flex flex-col gap-0.5 text-[12.5px] text-gray-800">
            {draft.references.map((ref, index) => (
              <li key={index} className="pl-3.5 -indent-3.5">
                • {ref}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}

function SidebarBlock({ draft, contact, accent }) {
  const languagesText = (lang) => joinTruthy([lang.name, lang.proficiency && `(${lang.proficiency})`], ' ')
  return (
    <>
      <div>
        {contact?.fullName && <p className="text-lg font-bold leading-tight text-white">{contact.fullName}</p>}
        {draft.title && (
          <p className="mt-0.5 text-[12.5px] font-medium" style={{ color: THEME.modern.accent }}>
            {draft.title}
          </p>
        )}
      </div>

      {(contact?.email || contact?.phone || contact?.location || contact?.linkedin || contact?.portfolio) && (
        <div className="flex flex-col gap-1 text-[11.5px]" style={{ color: THEME.modern.sidebarMuted }}>
          {contact.email && <p className="break-words">{contact.email}</p>}
          {contact.phone && <p>{contact.phone}</p>}
          {contact.location && <p>{contact.location}</p>}
          {contact.linkedin && <p className="break-words">{contact.linkedin}</p>}
          {contact.portfolio && <p className="break-words">{contact.portfolio}</p>}
        </div>
      )}

      {(draft.skills?.technical?.length > 0 || draft.skills?.soft?.length > 0) && (
        <div className="flex flex-col gap-2.5">
          <p className="text-[11px] font-bold uppercase tracking-wide" style={{ color: accent }}>
            Skills
          </p>
          {draft.skills.technical?.length > 0 && (
            <div>
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-wide" style={{ color: THEME.modern.sidebarMuted }}>
                Technical
              </p>
              <ul className="flex flex-col gap-0.5 text-[12px] text-gray-200">
                {draft.skills.technical.map((skill, index) => (
                  <li key={index}>{skill}</li>
                ))}
              </ul>
            </div>
          )}
          {draft.skills.soft?.length > 0 && (
            <div>
              <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-wide" style={{ color: THEME.modern.sidebarMuted }}>
                Soft Skills
              </p>
              <ul className="flex flex-col gap-0.5 text-[12px] text-gray-200">
                {draft.skills.soft.map((skill, index) => (
                  <li key={index}>{skill}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {draft.languages?.length > 0 && (
        <div>
          <p className="mb-1 text-[11px] font-bold uppercase tracking-wide" style={{ color: accent }}>
            Languages
          </p>
          <ul className="flex flex-col gap-0.5 text-[12px] text-gray-200">
            {draft.languages.map((lang, index) => (
              <li key={index}>{languagesText(lang)}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}

export default function ResumeDocument({ draft, template = 'professional' }) {
  const theme = THEME[template] || THEME.professional
  const contact = draft?.contact

  if (!hasResumeContent(draft)) {
    return null
  }

  if (template === 'modern') {
    return (
      <div className="flex min-h-full overflow-hidden bg-white text-gray-900">
        <div className="flex w-[34%] shrink-0 flex-col gap-5 p-5" style={{ backgroundColor: theme.sidebarBg }}>
          <SidebarBlock draft={draft} contact={contact} accent={theme.accent} />
        </div>
        <div className="flex flex-1 flex-col gap-4 p-5">
          <MainSections draft={draft} template={template} accent={theme.accent} />
        </div>
      </div>
    )
  }

  const skills = draft.skills || {}
  const hasSkills = skills.technical?.length > 0 || skills.soft?.length > 0

  return (
    <div className="flex flex-col gap-4 bg-white p-7 text-gray-900">
      {(contact?.fullName || draft.title || contact) && (
        <div
          className={
            template === 'minimalist' ? 'flex flex-col gap-0.5 border-b border-gray-200 pb-4' : 'flex flex-col items-center gap-0.5 text-center'
          }
        >
          {contact?.fullName && (
            <p
              className={template === 'executive' ? 'text-2xl font-bold tracking-wide' : 'text-xl font-bold'}
              style={{ fontFamily: theme.headingFont }}
            >
              {contact.fullName}
            </p>
          )}
          {draft.title && (
            <p className="text-[13px] font-medium" style={{ color: theme.accent }}>
              {draft.title}
            </p>
          )}
          <ContactLine contact={contact} className={template === 'minimalist' ? 'text-gray-500' : 'mt-0.5 text-gray-500'} />
          {template === 'executive' && <div className="mx-auto mt-2 h-px w-24" style={{ backgroundColor: theme.accent }} />}
        </div>
      )}

      {hasSkills && (
        <section>
          <Heading template={template} accent={theme.accent}>
            Core Skills
          </Heading>
          <div className={template === 'minimalist' ? 'flex flex-col gap-3' : 'grid grid-cols-2 gap-4'}>
            <SkillGroup label="Technical Skills" skills={skills.technical} accent={theme.accent} />
            <SkillGroup label="Soft Skills" skills={skills.soft} accent={theme.accent} />
          </div>
        </section>
      )}

      <MainSections draft={draft} template={template} accent={theme.accent} />
    </div>
  )
}
