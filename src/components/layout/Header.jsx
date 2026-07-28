import { Link } from 'react-router-dom'
import { Sun, Moon } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useTheme } from '../../theme/ThemeContext'
import { buttonClasses } from '../ui/Button'
import Logo from './Logo'

export default function Header() {
  const { isAuthenticated, isLoading } = useAuth()
  const { theme, toggle } = useTheme()
  const isLight = theme === 'light'

  return (
    <header className="border-b border-border bg-bg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-text-h">
          <Logo />
        </Link>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggle}
            title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
            className="flex h-9 w-9 items-center justify-center rounded-md border border-border text-text transition-colors hover:bg-border/40"
          >
            {isLight ? <Moon size={15} aria-hidden="true" /> : <Sun size={15} aria-hidden="true" />}
          </button>

          {!isLoading &&
            (isAuthenticated ? (
              <Link to="/dashboard" className={buttonClasses({ size: 'sm' })}>
                Go to dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-text hover:text-text-h">
                  Log in
                </Link>
                <Link to="/register" className={buttonClasses({ size: 'sm' })}>
                  Get started
                </Link>
              </>
            ))}
        </div>
      </div>
    </header>
  )
}
