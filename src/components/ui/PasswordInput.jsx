import { forwardRef, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { FieldWrapper, fieldBorderClass, useFieldIds } from './Field'

/** Password field with a show/hide toggle so users can check what they typed before submitting. */
const PasswordInput = forwardRef(function PasswordInput(
  { label, required, error, hint, id, className, ...props },
  ref
) {
  const ids = useFieldIds(id)
  const [visible, setVisible] = useState(false)

  return (
    <FieldWrapper {...ids} label={label} required={required} error={error} hint={hint}>
      <div className="relative">
        <input
          ref={ref}
          id={ids.id}
          type={visible ? 'text' : 'password'}
          required={required}
          aria-required={required || undefined}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error ? ids.errorId : hint ? ids.hintId : undefined}
          className={`${fieldBorderClass(error)} pr-10 ${className || ''}`}
          {...props}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex items-center px-3 text-text/60 hover:text-text-h"
        >
          {visible ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
        </button>
      </div>
    </FieldWrapper>
  )
})

export default PasswordInput
