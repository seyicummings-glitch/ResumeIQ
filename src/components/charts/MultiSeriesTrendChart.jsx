import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts'

/**
 * Multi-line time-series chart — e.g. resume uploads/analyses/downloads, or
 * interview started-vs-completed, plotted together for direct comparison.
 * @param {{data: Object[], xKey: string, series: {key: string, label: string, color: string}[]}} props
 */
export default function MultiSeriesTrendChart({ data, xKey, series }) {
  return (
    <div>
      <div style={{ width: '100%', height: 240 }} aria-hidden="true">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fill: 'var(--text)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} />
            <YAxis tick={{ fill: 'var(--text)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} />
            <Tooltip contentStyle={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {series.map(({ key, label, color }) => (
              <Line key={key} type="monotone" dataKey={key} name={label} stroke={color} strokeWidth={2} dot={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>{series.map((s) => s.label).join(' vs ')} over time</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            {series.map((s) => <th key={s.key} scope="col">{s.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row[xKey]}>
              <td>{row[xKey]}</td>
              {series.map((s) => <td key={s.key}>{row[s.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
