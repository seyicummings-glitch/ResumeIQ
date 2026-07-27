export default function Footer() {
  return (
    <footer className="border-t border-border py-6">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 text-sm text-text sm:flex-row">
        <span>© {new Date().getFullYear()} ResumeIQ</span>
        <span>AI-assisted resume analysis, built for job seekers</span>
      </div>
    </footer>
  )
}
