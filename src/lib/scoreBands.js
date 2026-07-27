/** Shared "score -> label/color" logic used everywhere a score appears (ScoreBadge, charts, history, admin analytics) so bands stay consistent across the app. */
export function getScoreBand(score) {
  if (score >= 75) return { label: 'Strong', tone: 'success' }
  if (score >= 50) return { label: 'Fair', tone: 'warning' }
  return { label: 'Needs work', tone: 'danger' }
}

export const SCORE_BAND_COLORS = {
  success: { text: 'text-success', bg: 'bg-success-bg', hex: '#15803d' },
  warning: { text: 'text-warning', bg: 'bg-warning-bg', hex: '#a15c00' },
  danger: { text: 'text-danger', bg: 'bg-danger-bg', hex: '#b91c1c' },
}
