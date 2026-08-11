import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './auth/AuthContext'
import { ThemeProvider } from './theme/ThemeContext'
import { ToastProvider } from './components/ui/Toast'
import { ResumeDraftProvider } from './resume/ResumeDraftContext'
import { ResumeBuilderDraftProvider } from './resume/ResumeBuilderDraftContext'
import { CareerCoachProvider } from './coach/CareerCoachContext'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // Without this, every query is considered stale the instant it loads, so navigating
      // back to a page you already visited (Dashboard -> History -> Dashboard) re-fetches
      // everything from scratch instead of showing the already-loaded data instantly — the
      // main reason page-to-page navigation felt slow. Mutations already call
      // invalidateQueries where data can actually change, so this doesn't risk showing stale
      // data after an edit — it only skips redundant re-fetches of unchanged data.
      staleTime: 60 * 1000,
    },
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <ToastProvider>
              <ResumeDraftProvider>
                <ResumeBuilderDraftProvider>
                  <CareerCoachProvider>
                    <App />
                  </CareerCoachProvider>
                </ResumeBuilderDraftProvider>
              </ResumeDraftProvider>
            </ToastProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
)
