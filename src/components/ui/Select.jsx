import { forwardRef } from 'react'
import { FieldWrapper, fieldBorderClass, useFieldIds } from './Field'

const Select = forwardRef(function Select({ label, required, error, hint, id, className, children, ...props }, ref) {
  const ids = useFieldIds(id)
  return (
    <FieldWrapper {...ids} label={label} required={required} error={error} hint={hint}>
      <select
        ref={ref}
        id={ids.id}
        required={required}
        aria-required={required || undefined}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error ? ids.errorId : hint ? ids.hintId : undefined}
        className={`${fieldBorderClass(error)} ${className || ''}`}
        {...props}
      >
        {children}
      </select>
    </FieldWrapper>
  )
})

export default Select
