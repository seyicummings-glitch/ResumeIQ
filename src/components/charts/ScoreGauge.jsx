import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts'
import { getScoreBand, SCORE_BAND_COLORS } from '../../lib/scoreBands'

/** Overall score as a single-ring gauge, with a visually-hidden text summary since SVG charts aren't reliably announced by screen readers. */
export default function ScoreGauge({ score, label = 'Overall score', size = 160 }) {
  const band = getScoreBand(score)
  const color = SCORE_BAND_COLORS[band.tone].hex
  const data = [{ name: label, value: score, fill: color }]

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }} aria-hidden="true">
        <RadialBarChart
          width={size}
          height={size}
          cx="50%"
          cy="50%"
          innerRadius="70%"
          outerRadius="100%"
          barSize={14}
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar dataKey="value" cornerRadius={8} background={{ fill: 'var(--border)' }} />
        </RadialBarChart>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-semibold text-text-h">{Math.round(score)}</span>
          <span className="text-xs text-text">/ 100</span>
        </div>
      </div>
      <p className="mt-2 text-sm font-medium" style={{ color }}>
        {label} · {band.label}
      </p>
      <span className="sr-only">
        {label}: {Math.round(score)} out of 100, {band.label.toLowerCase()}
      </span>
    </div>
  )
}
