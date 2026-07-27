import clsx from 'clsx'

export default function Card({ as: Component = 'div', className, children, ...props }) {
  return (
    <Component className={clsx('rounded-xl border border-border bg-surface p-5', className)} {...props}>
      {children}
    </Component>
  )
}
