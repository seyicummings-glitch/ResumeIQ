export const adminReportsSample = [
  { id: 'rep-1', reporterEmail: 'priya.natarajan@example.com', reason: 'Job description looks like spam / not a real posting', targetType: 'job_description', targetLabel: '"Work From Home - Earn $$$"', status: 'open', createdAt: '2026-07-21T12:00:00Z' },
  { id: 'rep-2', reporterEmail: 'lena.hoffmann@example.com', reason: 'AI suggestions returned an irrelevant result', targetType: 'resume', targetLabel: 'Lena_Hoffmann_CV.pdf', status: 'open', createdAt: '2026-07-19T08:40:00Z' },
  { id: 'rep-3', reporterEmail: 'a.rossi@example.com', reason: 'Duplicate job description posted twice', targetType: 'job_description', targetLabel: 'Senior Frontend Engineer', status: 'resolved', createdAt: '2026-07-12T15:20:00Z' },
  { id: 'rep-4', reporterEmail: 'jordan.cole@example.com', reason: 'Match score seemed inconsistent between runs', targetType: 'analysis', targetLabel: 'Jordan_Cole_Resume.pdf → Backend Engineer (Python)', status: 'dismissed', createdAt: '2026-07-08T10:05:00Z' },
]
