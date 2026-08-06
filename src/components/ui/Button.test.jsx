import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Button, { buttonClasses } from './Button'

describe('Button', () => {
  it('renders children and responds to clicks', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Save as new version</Button>)

    const button = screen.getByRole('button', { name: 'Save as new version' })
    await user.click(button)

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled and does not fire onClick when disabled', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <Button onClick={onClick} disabled>
        Generate
      </Button>
    )

    const button = screen.getByRole('button', { name: 'Generate' })
    expect(button).toBeDisabled()
    await user.click(button)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('is disabled and marked busy while isLoading, even without an explicit disabled prop', () => {
    render(<Button isLoading>Saving…</Button>)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('aria-busy', 'true')
  })

  it('defaults to type="button" so it never accidentally submits a form', () => {
    render(<Button>Attach</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button')
  })

  it('respects an explicit type="submit"', () => {
    render(<Button type="submit">Send</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit')
  })
})

describe('buttonClasses', () => {
  it('includes the variant, size, and any extra className', () => {
    const classes = buttonClasses({ variant: 'secondary', size: 'sm', className: 'underline' })
    expect(classes).toContain('underline')
    expect(classes).toMatch(/border/)
  })

  it('defaults to the primary variant and md size', () => {
    const classes = buttonClasses()
    expect(classes).toContain('bg-accent')
  })
})
