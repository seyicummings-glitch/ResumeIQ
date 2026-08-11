import { ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import Button from './Button'

const SIBLING_COUNT = 2

function buildPageList(page, totalPages) {
  const pages = new Set([1, totalPages, page])
  for (let offset = 1; offset <= SIBLING_COUNT; offset += 1) {
    if (page - offset >= 1) pages.add(page - offset)
    if (page + offset <= totalPages) pages.add(page + offset)
  }
  const sorted = [...pages].sort((a, b) => a - b)

  const withGaps = []
  sorted.forEach((pageNumber, index) => {
    if (index > 0 && pageNumber - sorted[index - 1] > 1) withGaps.push('gap')
    withGaps.push(pageNumber)
  })
  return withGaps
}

export default function Pagination({ page, pageSize, total, onPageChange }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (totalPages <= 1) return null

  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  const pageList = buildPageList(page, totalPages)

  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 pt-2">
      <p className="text-sm text-text">
        Showing {start}–{end} of {total}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </Button>
        {pageList.map((entry, index) =>
          entry === 'gap' ? (
            <span key={`gap-${index}`} className="px-1.5 text-sm text-text/60" aria-hidden="true">
              …
            </span>
          ) : (
            <button
              key={entry}
              type="button"
              onClick={() => onPageChange(entry)}
              aria-current={entry === page ? 'page' : undefined}
              className={clsx(
                'min-w-8 rounded-md px-2 py-1.5 text-sm font-medium transition-colors',
                entry === page
                  ? 'bg-accent text-accent-contrast'
                  : 'text-text-h hover:bg-surface'
              )}
            >
              {entry}
            </button>
          )
        )}
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          <ChevronRight size={16} aria-hidden="true" />
        </Button>
      </div>
    </nav>
  )
}
