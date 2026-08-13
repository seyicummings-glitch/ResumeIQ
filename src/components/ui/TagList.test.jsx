import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TagList from './TagList'

describe('TagList', () => {
  it('renders nothing when items is empty or missing', () => {
    const { container: emptyContainer } = render(<TagList items={[]} />)
    expect(emptyContainer).toBeEmptyDOMElement()

    const { container: undefinedContainer } = render(<TagList items={undefined} />)
    expect(undefinedContainer).toBeEmptyDOMElement()
  })

  it('renders all items with no "more" badge when under the max', () => {
    render(<TagList items={['Python', 'SQL']} max={6} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('SQL')).toBeInTheDocument()
    expect(screen.queryByText(/more/i)).not.toBeInTheDocument()
  })

  it('truncates to max items and shows a "+N more" badge', () => {
    render(<TagList items={['A', 'B', 'C', 'D', 'E']} max={3} />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('C')).toBeInTheDocument()
    expect(screen.queryByText('D')).not.toBeInTheDocument()
    expect(screen.getByText('+2 more')).toBeInTheDocument()
  })

  it('opens a modal listing every item when the "more" badge is clicked', async () => {
    const user = userEvent.setup()
    render(<TagList items={['A', 'B', 'C', 'D', 'E']} max={3} label="skills" />)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /show all 5 skills/i }))

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    // 'D' and 'E' only appear inside the modal, not in the truncated inline list
    expect(screen.getAllByText('D')).toHaveLength(1)
    expect(screen.getAllByText('E')).toHaveLength(1)
  })
})
