import Badge from '../../components/ui/Badge'

export default function JobDescriptionAnalysisResult({ analysis }) {
  const { required_skills: requiredSkills, experience_level: experienceLevel, qualifications } = analysis

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm text-text">Experience level</p>
        <p className="font-medium text-text-h">{experienceLevel}</p>
      </div>

      <div>
        <p className="mb-1.5 text-sm text-text">Required skills / keywords</p>
        {requiredSkills.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {requiredSkills.map((skill) => (
              <Badge key={skill} tone="accent">
                {skill}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-text">None detected.</p>
        )}
      </div>

      <div>
        <p className="mb-1.5 text-sm text-text">Qualifications mentioned</p>
        {qualifications.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {qualifications.map((qualification) => (
              <li key={qualification} className="text-sm text-text-h">
                • {qualification}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text">None detected.</p>
        )}
      </div>
    </div>
  )
}
