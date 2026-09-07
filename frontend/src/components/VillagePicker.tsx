import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { MicButton } from './MicButton'
import type { VillageMatch } from '../types'

interface Props {
  value: VillageMatch | null
  onChange: (village: VillageMatch | null) => void
  state: string
  language: 'en' | 'hi'
  strings: {
    village: string
    villagePlaceholder: string
    confirm: string
    speak: string
    listening: string
    micUnsupported: string
  }
}

/** The matcher returns a ranked shortlist; the user picks. Never auto-select — a wrong village
 *  silently poisons every number downstream. */
export function VillagePicker({ value, onChange, state, language, strings }: Props) {
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState<VillageMatch[]>([])
  const [searching, setSearching] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => {
    window.clearTimeout(timer.current)
    if (!query.trim() || value) {
      setMatches([])
      return
    }
    setSearching(true)
    timer.current = window.setTimeout(async () => {
      try {
        setMatches(await api.searchVillages(query.trim(), state))
      } catch {
        setMatches([])
      } finally {
        setSearching(false)
      }
    }, 220)
    return () => window.clearTimeout(timer.current)
  }, [query, state, value])

  if (value) {
    return (
      <div>
        <label className="block text-sm font-medium text-ink-2">{strings.village}</label>
        <div className="mt-1.5 flex items-center justify-between gap-3 rounded-lg border border-hairline bg-surface px-4 py-3">
          <span className="text-base font-medium text-ink">
            {language === 'hi' && value.name_hi ? value.name_hi : value.name}
            <span className="ml-2 text-sm font-normal text-ink-2">
              {value.block} · {value.district}
            </span>
          </span>
          <button
            type="button"
            onClick={() => {
              onChange(null)
              setQuery('')
            }}
            className="shrink-0 text-sm font-medium text-accent underline underline-offset-2"
          >
            {language === 'en' ? 'Change' : 'बदलें'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <label htmlFor="village" className="block text-sm font-medium text-ink-2">
        {strings.village}
      </label>
      <div className="mt-1.5 flex gap-2">
        <input
          id="village"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={strings.villagePlaceholder}
          autoComplete="off"
          className="min-w-0 flex-1 rounded-lg border border-hairline bg-surface px-4 py-3 text-base text-ink outline-none focus:border-accent"
        />
        <MicButton onResult={setQuery} language={language} strings={strings} />
      </div>

      {searching && <p className="mt-2 text-xs text-ink-muted">…</p>}

      {matches.length > 0 && (
        <div className="mt-2">
          <p className="mb-1.5 text-xs text-ink-muted">{strings.confirm}</p>
          <ul className="space-y-1.5">
            {matches.map((m) => (
              <li key={m.shrid}>
                <button
                  type="button"
                  onClick={() => onChange(m)}
                  className="flex w-full items-center justify-between gap-3 rounded-lg border border-hairline bg-surface px-4 py-3 text-left hover:border-accent"
                >
                  <span>
                    <span className="text-base font-medium text-ink">
                      {m.name}
                      {m.name_hi && <span className="ml-2 text-ink-2">{m.name_hi}</span>}
                    </span>
                    <span className="block text-xs text-ink-2">
                      {m.block} · {m.district} — {m.reason}
                    </span>
                  </span>
                  <span className="tabular shrink-0 text-xs text-ink-muted">
                    {Math.round(m.score * 100)}%
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!searching && query.trim() && matches.length === 0 && (
        <p className="mt-2 text-xs text-ink-2">
          {language === 'en'
            ? 'No village matched. Try another spelling.'
            : 'कोई गाँव नहीं मिला। दूसरी वर्तनी आज़माएँ।'}
        </p>
      )}
    </div>
  )
}
