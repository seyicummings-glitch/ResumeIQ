import { useId } from 'react'
import clsx from 'clsx'

const fieldClasses =
  'w-full rounded-lg border bg-bg px-3 py-2 text-text-h placeholder:text-text/60 disabled:opacity-50 transition-colors'

/** Shared label/error/hint chrome for form fields — used by Input/TextArea/Select so every field announces errors the same accessible way. */
export function useFieldIds(idProp) {
  const generatedId = useId()
  const id = idProp || generatedId
  return { id, errorId: `${id}-error`, hintId: `${id}-hint` }
}

export function FieldWrapper({ id, errorId, hintId, label, required, error, hint, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-text-h">
          {label}
          {required && (
            <span aria-hidden="true" className="text-danger">
              {' '}
              *
            </span>
          )}
        </label>
      )}
      {children}
      {hint && !error && (
        <p id={hintId} className="text-xs text-text">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export function fieldBorderClass(error) {
  return clsx(fieldClasses, error ? 'border-danger focus-visible:outline-danger' : 'border-border focus-visible:outline-accent')
}
