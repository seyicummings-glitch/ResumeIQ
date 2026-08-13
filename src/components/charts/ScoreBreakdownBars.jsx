import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { getScoreBand, SCORE_BAND_COLORS } from '../../lib/scoreBands'

/**
 * Grouped bar chart for the skill/experience/qualification (and optional
 * GitHub) sub-scores that make up an overall match score.
 * @param {{items: {label: string, score: number}[], caption?: string}} props
 */
export default function ScoreBreakdownBars({ items, caption }) {
  const data = items.map((item) => ({ ...item, fill: SCORE_BAND_COLORS[getScoreBand(item.score).tone].hex }))
  const summary = items.map((item) => `${item.label}: ${Math.round(item.score)}`).join(', ')

  return (
    <div>
      <div style={{ width: '100%', height: 180 }} aria-hidden="true">
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
            <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--text)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
            <YAxis type="category" dataKey="label" width={110} tick={{ fill: 'var(--text-h)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
            <Tooltip
              formatter={(value) => [`${Math.round(value)}`, 'Score']}
              contentStyle={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8 }}
            />
            <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={18}>
              {data.map((entry) => (
                <Cell key={entry.label} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {caption && <p className="mt-1 text-xs text-text">{caption}</p>}
      <span className="sr-only">Score breakdown: {summary}</span>
    </div>
  )
}
