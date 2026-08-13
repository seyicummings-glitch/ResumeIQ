import { Outlet } from 'react-router-dom'
import SkipToContentLink from './SkipToContentLink'
import Header from './Header'
import Footer from './Footer'

export default function PublicShell() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-text">
      <SkipToContentLink />
      <Header />
      <main id="main-content" tabIndex={-1} className="flex-1 px-4">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
