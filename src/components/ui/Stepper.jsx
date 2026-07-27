import { Check } from 'lucide-react'
import clsx from 'clsx'

/** @param {{steps: string[], currentStep: number}} props - currentStep is 0-indexed */
export default function Stepper({ steps, currentStep }) {
  return (
    <ol className="flex items-center gap-2" aria-label="Progress">
      {steps.map((step, index) => {
        const isComplete = index < currentStep
        const isCurrent = index === currentStep
        return (
          <li key={step} className="flex items-center gap-2">
            <span
              className={clsx(
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                isComplete && 'bg-success text-white',
                isCurrent && 'bg-accent text-accent-contrast',
                !isComplete && !isCurrent && 'bg-border text-text'
              )}
              aria-current={isCurrent ? 'step' : undefined}
            >
              {isComplete ? <Check size={14} aria-hidden="true" /> : index + 1}
            </span>
            <span className={clsx('text-sm', isCurrent ? 'font-medium text-text-h' : 'text-text')}>{step}</span>
            {index < steps.length - 1 && <span className="mx-1 h-px w-6 bg-border" aria-hidden="true" />}
          </li>
        )
      })}
    </ol>
  )
}
