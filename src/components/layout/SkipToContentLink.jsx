export default function SkipToContentLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only fixed left-2 top-2 z-[60] rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-contrast"
    >
      Skip to main content
    </a>
  )
}
