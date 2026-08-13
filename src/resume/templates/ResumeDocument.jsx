/**
 * Renders a structured resume draft as a real document layout — a clean, professional,
 * ATS-safe single-column resume. Deliberately rendered as a fixed light "paper" page (not the
 * app's dark/light theme) since this is meant to look like something you'd send to a recruiter,
 * not app chrome.
 */
const ACCENT = '#2563eb'

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

function Heading({ children }) {
  return (
    <p className="mb-2 border-b-2 pb-1 text-[12px] font-bold uppercase tracking-wide text-gray-900" style={{ borderColor: ACCENT }}>
      {children}
    </p>
  )
}

function SkillGroup({ label, skills }) {
  if (!skills?.length) return null
  return (
    <div>
      <p className="mb-1 text-[11px] font-bold uppercase tracking-wide" style={{ color: ACCENT }}>
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

function ExperienceEntry({ job }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[13.5px] font-bold text-gray-900">{job.title || '(untitled role)'}</p>
        {dateRange(job) && <p className="shrink-0 text-[11.5px] text-gray-500">{dateRange(job)}</p>}
      </div>
      {job.company && (
        <p className="text-[12.5px] font-medium" style={{ color: ACCENT }}>
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

function ContactLine({ contact }) {
  const line = joinTruthy([contact?.email, contact?.phone, contact?.location, contact?.linkedin, contact?.portfolio], '   |   ')
  if (!line) return null
  return <p className="mt-0.5 text-[11.5px] text-gray-500">{line}</p>
}

export default function ResumeDocument({ draft }) {
  const contact = draft?.contact
  const skills = draft?.skills || {}
  const hasSkills = skills.technical?.length > 0 || skills.soft?.length > 0

  if (!hasResumeContent(draft)) {
    return null
  }

  return (
    <div className="flex flex-col gap-4 bg-white p-7 text-gray-900">
      {(contact?.fullName || draft.title || contact) && (
        <div className="flex flex-col items-center gap-0.5 text-center">
          {contact?.fullName && <p className="text-xl font-bold">{contact.fullName}</p>}
          {draft.title && (
            <p className="text-[13px] font-medium" style={{ color: ACCENT }}>
              {draft.title}
            </p>
          )}
          <ContactLine contact={contact} />
        </div>
      )}

      {draft.summary && (
        <section>
          <Heading>Professional Summary</Heading>
          <p className="text-[13px] leading-relaxed text-gray-800">{draft.summary}</p>
        </section>
      )}

      {hasSkills && (
        <section>
          <Heading>Core Skills</Heading>
          <div className="grid grid-cols-2 gap-4">
            <SkillGroup label="Technical Skills" skills={skills.technical} />
            <SkillGroup label="Soft Skills" skills={skills.soft} />
          </div>
        </section>
      )}

      {draft.experience?.length > 0 && (
        <section>
          <Heading>Professional Experience</Heading>
          <div className="flex flex-col gap-3">
            {draft.experience.map((job, index) => (
              <ExperienceEntry key={index} job={job} />
            ))}
          </div>
        </section>
      )}

      {draft.education?.length > 0 && (
        <section>
          <Heading>Education</Heading>
          <div className="flex flex-col gap-1.5">
            {draft.education.map((edu, index) => (
              <EducationEntry key={index} edu={edu} />
            ))}
          </div>
        </section>
      )}

      {draft.projects?.length > 0 && (
        <section>
          <Heading>Projects</Heading>
          <div className="flex flex-col gap-2.5">
            {draft.projects.map((project, index) => (
              <ProjectEntry key={index} project={project} />
            ))}
          </div>
        </section>
      )}

      {draft.certifications?.length > 0 && (
        <section>
          <Heading>Certifications</Heading>
          <ul className="flex flex-col gap-0.5 text-[12.5px] text-gray-800">
            {draft.certifications.map((cert, index) => (
              <li key={index} className="pl-3.5 -indent-3.5">
                • {cert}
              </li>
            ))}
          </ul>
        </section>
      )}

      {draft.languages?.length > 0 && (
        <section>
          <Heading>Languages</Heading>
          <ul className="flex flex-col gap-0.5 text-[12.5px] text-gray-800">
            {draft.languages.map((lang, index) => (
              <li key={index} className="pl-3.5 -indent-3.5">
                • {joinTruthy([lang.name, lang.proficiency && `(${lang.proficiency})`], ' ')}
              </li>
            ))}
          </ul>
        </section>
      )}

      {draft.references?.length > 0 && (
        <section>
          <Heading>References</Heading>
          <ul className="flex flex-col gap-0.5 text-[12.5px] text-gray-800">
            {draft.references.map((ref, index) => (
              <li key={index} className="pl-3.5 -indent-3.5">
                • {ref}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
