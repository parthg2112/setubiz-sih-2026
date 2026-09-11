import { useCallback, useEffect, useState } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useSearchParams,
} from 'react-router-dom'
import { SiteFooter } from './components/layout/SiteFooter'
import { SiteHeader } from './components/layout/SiteHeader'
import { TopBar } from './components/layout/TopBar'
import { T } from './format'
import { Ask } from './pages/Ask'
import { NotFound } from './pages/NotFound'
import { Report } from './pages/Report'
import { applyScale, storedScale, type TextScale } from './textScale'
import { applyTheme, storedTheme, watchSystemTheme, type ThemeChoice } from './theme'
import type { Language } from './types'
import { languageFromParams } from './urlState'

/** Build date for the footer's "last updated". Vite inlines this at build time. */
const BUILD_DATE = new Date().toISOString().slice(0, 10)

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  )
}

function Shell() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()

  // A shared link opens in the language it was shared in; otherwise English.
  const [language, setLanguage] = useState<Language>(() => languageFromParams(params) ?? 'en')
  const [theme, setTheme] = useState<ThemeChoice>(storedTheme)
  const [scale, setScale] = useState<TextScale>(storedScale)
  const [busy, setBusy] = useState(false)

  const strings = T[language]

  useEffect(() => applyTheme(theme), [theme])
  useEffect(() => watchSystemTheme(() => theme), [theme])
  useEffect(() => applyScale(scale), [scale])

  /** The previous build left <html lang="en"> permanently, so assistive technology announced
   *  Devanagari with an English voice. */
  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const switchLanguage = useCallback(
    (next: Language) => {
      setLanguage(next)
      // On a report, language lives in the URL so the change is shareable and survives reload.
      if (params.has('lang')) {
        const updated = new URLSearchParams(params)
        updated.set('lang', next)
        setParams(updated, { replace: true })
      }
    },
    [params, setParams],
  )

  return (
    <>
      <TopBar
        strings={strings}
        language={language}
        onLanguage={switchLanguage}
        scale={scale}
        onScale={setScale}
        busy={busy}
      />
      <SiteHeader strings={strings} theme={theme} onTheme={setTheme} />

      <main id="main-content" tabIndex={-1}>
        <Routes>
          <Route
            path="/"
            element={
              <Ask
                language={language}
                strings={strings}
                onSubmit={(search) => navigate({ pathname: '/report', search })}
              />
            }
          />
          <Route
            path="/report"
            element={
              <Report
                language={language}
                strings={strings}
                onBusyChange={setBusy}
                onRestart={() => navigate('/')}
              />
            }
          />
          <Route path="/index.html" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFound strings={strings} />} />
        </Routes>
      </main>

      <SiteFooter strings={strings} buildDate={BUILD_DATE} />
    </>
  )
}
