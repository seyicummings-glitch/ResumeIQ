import { forwardRef } from 'react'
import clsx from 'clsx'
import { LoaderCircle } from 'lucide-react'

const VARIANT_CLASSES = {
  primary: 'bg-accent text-accent-contrast hover:opacity-90 disabled:opacity-50',
  secondary: 'bg-surface text-text-h border border-border hover:bg-border/40 disabled:opacity-50',
  ghost: 'text-text-h hover:bg-surface disabled:opacity-50',
  danger: 'bg-danger text-white hover:opacity-90 disabled:opacity-50',
}

const SIZE_CLASSES = {
  sm: 'text-sm px-3 py-1.5 gap-1.5',
  md: 'text-sm px-4 py-2 gap-2',
  lg: 'text-base px-5 py-2.5 gap-2',
}

/** Shared visual classes so a react-router <Link> can look exactly like a Button when a nav action needs to be a real link, not a <button onClick={navigate}>. */
export function buttonClasses({ variant = 'primary', size = 'md', className } = {}) {
  return clsx(
    'inline-flex items-center justify-center rounded-lg font-medium transition-colors cursor-pointer disabled:cursor-not-allowed',
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
    className
  )
}

const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', isLoading = false, disabled, className, children, type = 'button', ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={buttonClasses({ variant, size, className })}
      {...props}
    >
      {isLoading && <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />}
      {children}
    </button>
  )
})

export default Button
