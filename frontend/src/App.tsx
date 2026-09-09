import { useEffect, useState } from 'react'
import { api, type AdvisoryInput } from './api'
import { T } from './format'
import { Ask } from './pages/Ask'
import { Report } from './pages/Report'
import { applyTheme, storedTheme, watchSystemTheme, type ThemeChoice } from './theme'
import type { AdvisoryResponse, Language } from './types'

export default function App() {
  const [language, setLanguage] = useState<Language>('en')
  const [theme, setTheme] = useState<ThemeChoice>(storedTheme)
  const [data, setData] = useState<AdvisoryResponse | null>(null)
  const [lastInput, setLastInput] = useState<AdvisoryInput | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const strings = T[language]

  useEffect(() => applyTheme(theme), [theme])
  useEffect(() => watchSystemTheme(() => theme), [theme])

  async function run(input: AdvisoryInput, forLanguage: Language = language) {
    setBusy(true)
    setError(null)
    setLastInput(input)
    try {
      setData(await api.advisory({ ...input, language: forLanguage }))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  /** The narrated prose is produced server-side per language, so switching languages on a
   *  finished report has to re-run the pipeline — translating in the client would be exactly the
   *  drift the bilingual-at-source rule exists to prevent. */
  function switchLanguage(next: Language) {
    setLanguage(next)
    if (data && lastInput) void run(lastInput, next)
  }

  return (
    <div className="min-h-full">
      <header className="no-print sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[1400px] items-center justify-between gap-4 px-4 py-3 lg:px-8">
          <div className="min-w-0">
            <p className="truncate text-base font-semibold tracking-tight text-foreground">
              {strings.appName}
            </p>
            <p className="hidden truncate text-xs text-muted-foreground sm:block">
              {strings.tagline}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Segmented
              label={strings.theme}
              value={theme}
              onChange={(next) => setTheme(next as ThemeChoice)}
              options={[
                { value: 'system', label: '◐', title: strings.themeSystem },
                { value: 'light', label: '☀', title: strings.themeLight },
                { value: 'dark', label: '☾', title: strings.themeDark },
              ]}
            />
            <Segmented
              label="Language"
              value={language}
              onChange={(next) => switchLanguage(next as Language)}
              disabled={busy}
              options={[
                { value: 'en', label: 'EN', title: 'English' },
                { value: 'hi', label: 'हिं', title: 'हिन्दी' },
              ]}
            />
          </div>
        </div>
      </header>

      <main>
        {data ? (
          <Report
            data={data}
            language={language}
            strings={strings}
            onRestart={() => setData(null)}
          />
        ) : (
          <Ask
            language={language}
            strings={strings}
            onSubmit={(input) => run(input)}
            busy={busy}
            error={error}
          />
        )}
      </main>
    </div>
  )
}

function Segmented({
  label,
  value,
  onChange,
  options,
  disabled = false,
}: {
  label: string
  value: string
  onChange: (next: string) => void
  options: { value: string; label: string; title: string }[]
  disabled?: boolean
}) {
  return (
    <div
      className="flex shrink-0 overflow-hidden rounded-full border border-border"
      role="group"
      aria-label={label}
    >
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={active}
            title={option.title}
            disabled={disabled}
            className={`px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 ${
              active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
