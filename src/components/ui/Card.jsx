import clsx from 'clsx'

export default function Card({ as: Component = 'div', className, children, ...props }) {
  return (
    <Component className={clsx('rounded-lg border border-border bg-surface p-5', className)} {...props}>
      {children}
    </Component>
  )
}
