import { forwardRef } from 'react'
import { FieldWrapper, fieldBorderClass, useFieldIds } from './Field'

const Input = forwardRef(function Input({ label, required, error, hint, id, className, ...props }, ref) {
  const ids = useFieldIds(id)
  return (
    <FieldWrapper {...ids} label={label} required={required} error={error} hint={hint}>
      <input
        ref={ref}
        id={ids.id}
        required={required}
        aria-required={required || undefined}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error ? ids.errorId : hint ? ids.hintId : undefined}
        className={`${fieldBorderClass(error)} ${className || ''}`}
        {...props}
      />
    </FieldWrapper>
  )
})

export default Input
