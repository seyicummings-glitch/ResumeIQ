function lastNDays(n, seedFn) {
  const days = []
  const today = new Date('2026-07-24T00:00:00Z')
  for (let i = n - 1; i >= 0; i--) {
    const date = new Date(today)
    date.setUTCDate(date.getUTCDate() - i)
    days.push({ date: date.toISOString().slice(0, 10), value: seedFn(n - 1 - i) })
  }
  return days
}

export const adminAnalyticsSample = {
  signupsOverTime: lastNDays(14, (i) => Math.max(0, Math.round(3 + 2 * Math.sin(i / 2) + (i % 3)))).map((d) => ({
    date: d.date,
    signups: d.value,
  })),
  analysesPerDay: lastNDays(14, (i) => Math.max(0, Math.round(12 + 6 * Math.sin(i / 3) + (i % 4)))).map((d) => ({
    date: d.date,
    analyses: d.value,
  })),
  averageScoreTrend: lastNDays(14, (i) => Math.round(60 + 10 * Math.sin(i / 4) + (i % 5))).map((d) => ({
    date: d.date,
    averageScore: d.value,
  })),
  topMissingSkills: [
    { skill: 'kubernetes', count: 41 },
    { skill: 'aws', count: 37 },
    { skill: 'typescript', count: 29 },
    { skill: 'graphql', count: 22 },
    { skill: 'docker', count: 19 },
  ],
  summary: {
    totalUsers: 6,
    totalResumesAnalyzed: 213,
    totalJobDescriptions: 58,
    averageMatchScore: 68,
  },
}
