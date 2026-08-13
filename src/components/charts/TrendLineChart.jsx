import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

/**
 * Simple time-series line chart used by the admin analytics dashboard.
 * @param {{data: Object[], xKey: string, yKey: string, label: string, color?: string}} props
 */
export default function TrendLineChart({ data, xKey, yKey, label, color = 'var(--color-accent)' }) {
  return (
    <div>
      <div style={{ width: '100%', height: 220 }} aria-hidden="true">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fill: 'var(--text)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} />
            <YAxis tick={{ fill: 'var(--text)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} />
            <Tooltip contentStyle={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8 }} />
            <Line type="monotone" dataKey={yKey} name={label} stroke={color} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>{label} over time</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">{label}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row[xKey]}>
              <td>{row[xKey]}</td>
              <td>{row[yKey]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
