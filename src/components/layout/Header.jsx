import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Menu, X, FileSearch } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../auth/AuthContext'
import Button from '../ui/Button'

const PUBLIC_LINKS = []
const AUTHED_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/resume/upload', label: 'Upload resume' },
  { to: '/job-description/new', label: 'Job description' },
  { to: '/history', label: 'History' },
  { to: '/profile', label: 'Profile' },
]
const ADMIN_LINKS = [{ to: '/admin/users', label: 'Admin' }]

function navLinkClass({ isActive }) {
  return clsx('rounded-lg px-3 py-2 text-sm font-medium transition-colors', isActive ? 'text-accent' : 'text-text hover:text-text-h')
}

export default function Header() {
  const { isAuthenticated, isAdmin, isLoading, user, logout } = useAuth()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const navigate = useNavigate()

  const links = isAuthenticated ? [...AUTHED_LINKS, ...(isAdmin ? ADMIN_LINKS : [])] : PUBLIC_LINKS

  function handleLogout() {
    logout()
    setIsMenuOpen(false)
    navigate('/')
  }

  return (
    <header className="border-b border-border bg-bg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-text-h" onClick={() => setIsMenuOpen(false)}>
          <FileSearch size={22} className="text-accent" aria-hidden="true" />
          <span className="text-lg font-semibold">ResumeIQ</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
          {!isLoading &&
            links.map((link) => (
              <NavLink key={link.to} to={link.to} className={navLinkClass}>
                {link.label}
              </NavLink>
            ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          {isLoading ? null : isAuthenticated ? (
            <>
              <span className="px-2 text-sm text-text">{user?.full_name || user?.email}</span>
              <Button variant="secondary" size="sm" onClick={handleLogout}>
                Log out
              </Button>
            </>
          ) : (
            <>
              <Link to="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-text hover:text-text-h">
                Log in
              </Link>
              <Link to="/register" className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-contrast hover:opacity-90">
                Get started
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          className="md:hidden"
          onClick={() => setIsMenuOpen((open) => !open)}
          aria-expanded={isMenuOpen}
          aria-controls="mobile-nav"
          aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
        >
          {isMenuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
        </button>
      </div>

      {isMenuOpen && !isLoading && (
        <nav id="mobile-nav" aria-label="Main" className="flex flex-col gap-1 border-t border-border px-4 py-3 md:hidden">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} className={navLinkClass} onClick={() => setIsMenuOpen(false)}>
              {link.label}
            </NavLink>
          ))}
          {isAuthenticated ? (
            <Button variant="secondary" size="sm" className="mt-2 w-fit" onClick={handleLogout}>
              Log out
            </Button>
          ) : (
            <div className="mt-2 flex gap-2">
              <Link to="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-text" onClick={() => setIsMenuOpen(false)}>
                Log in
              </Link>
              <Link to="/register" className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-contrast" onClick={() => setIsMenuOpen(false)}>
                Get started
              </Link>
            </div>
          )}
        </nav>
      )}
    </header>
  )
}
