import { forwardRef } from 'react'
import { FieldWrapper, fieldBorderClass, useFieldIds } from './Field'

const TextArea = forwardRef(function TextArea({ label, required, error, hint, id, className, rows = 6, ...props }, ref) {
  const ids = useFieldIds(id)
  return (
    <FieldWrapper {...ids} label={label} required={required} error={error} hint={hint}>
      <textarea
        ref={ref}
        id={ids.id}
        rows={rows}
        required={required}
        aria-required={required || undefined}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error ? ids.errorId : hint ? ids.hintId : undefined}
        className={`${fieldBorderClass(error)} resize-y ${className || ''}`}
        {...props}
      />
    </FieldWrapper>
  )
})

export default TextArea
