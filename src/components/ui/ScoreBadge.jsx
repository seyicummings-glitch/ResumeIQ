import Badge from './Badge'
import { getScoreBand } from '../../lib/scoreBands'

/** Score + text label together, always — color is never the only signal (accessibility requirement). */
export default function ScoreBadge({ score, className }) {
  const band = getScoreBand(score)
  return (
    <Badge tone={band.tone} className={className}>
      {Math.round(score)} · {band.label}
    </Badge>
  )
}
