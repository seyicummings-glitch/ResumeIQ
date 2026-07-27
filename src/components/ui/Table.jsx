import clsx from 'clsx'

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

export function Th({ className, children, ...props }) {
  return (
    <th scope="col" className={clsx('border-b border-border px-4 py-3 font-medium', className)} {...props}>
      {children}
    </th>
  )
}

export function TableBody({ children }) {
  return <tbody className="divide-y divide-border">{children}</tbody>
}

export function Td({ className, children, ...props }) {
  return (
    <td className={clsx('px-4 py-3 text-text-h', className)} {...props}>
      {children}
    </td>
  )
}
