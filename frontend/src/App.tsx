import { useState } from 'react'
import { api, type AdvisoryInput } from './api'
import { T } from './format'
import { Ask } from './pages/Ask'
import { Report } from './pages/Report'
import type { AdvisoryResponse, Language } from './types'

export default function App() {
  const [language, setLanguage] = useState<Language>('en')
  const [data, setData] = useState<AdvisoryResponse | null>(null)
  const [lastInput, setLastInput] = useState<AdvisoryInput | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const strings = T[language]

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
      <header className="no-print border-b border-hairline bg-surface">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-4 py-3">
          <div>
            <p className="text-base font-semibold tracking-tight text-ink">{strings.appName}</p>
            <p className="text-xs text-ink-2">{strings.tagline}</p>
          </div>
          <div
            className="flex shrink-0 overflow-hidden rounded-lg border border-hairline"
            role="group"
            aria-label="Language"
          >
            {(['en', 'hi'] as const).map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => switchLanguage(code)}
                aria-pressed={language === code}
                disabled={busy}
                className="px-3 py-1.5 text-sm font-medium"
                style={{
                  background: language === code ? 'var(--accent)' : 'transparent',
                  color: language === code ? '#fff' : 'var(--text-secondary)',
                }}
              >
                {code === 'en' ? 'EN' : 'हिं'}
              </button>
            ))}
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
