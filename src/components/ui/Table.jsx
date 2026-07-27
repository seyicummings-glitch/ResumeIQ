export function Table({ children }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-max border-collapse text-left text-sm">{children}</table>
    </div>
  )
}

export function TableHead({ children }) {
  return (
    <thead className="bg-surface text-xs uppercase tracking-wide text-text">
      <tr>{children}</tr>
    </thead>
  )
}

export function Th({ children, ...props }) {
  return (
    <th scope="col" className="border-b border-border px-4 py-3 font-medium" {...props}>
      {children}
    </th>
  )
}

export function TableBody({ children }) {
  return <tbody className="divide-y divide-border">{children}</tbody>
}

export function Td({ children, ...props }) {
  return (
    <td className="px-4 py-3 text-text-h" {...props}>
      {children}
    </td>
  )
}
