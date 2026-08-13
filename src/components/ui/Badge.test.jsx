import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Badge from './Badge'

describe('Badge', () => {
  it('renders its children', () => {
    render(<Badge>AI-generated</Badge>)
    expect(screen.getByText('AI-generated')).toBeInTheDocument()
  })

  it('defaults to the neutral tone', () => {
    render(<Badge>Neutral</Badge>)
    expect(screen.getByText('Neutral')).toHaveClass('bg-border/40')
  })

  it('applies the class for a given tone', () => {
    render(<Badge tone="danger">Missing</Badge>)
    expect(screen.getByText('Missing')).toHaveClass('bg-danger-bg', 'text-danger')
  })

  it('merges a custom className with the tone classes', () => {
    render(
      <Badge tone="accent" className="mb-2">
        Skills
      </Badge>
    )
    expect(screen.getByText('Skills')).toHaveClass('bg-accent/10', 'mb-2')
  })
})
