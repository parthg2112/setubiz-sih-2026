import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import type { Strings } from '../format'
import { MicButton } from './MicButton'
import type { Language, VillageMatch } from '../types'

interface Props {
  value: VillageMatch | null
  onChange: (village: VillageMatch | null) => void
  state: string
  language: Language
  strings: Strings
}

/** The matcher returns a ranked shortlist; the user picks. Never auto-select — a wrong village
 *  silently poisons every number downstream.
 *
 *  The score is deliberately not shown as a percentage. "85%" invites a reader to weigh two
 *  numbers they have no basis to compare; "Closest match" plus the matcher's own written reason
 *  ("sounds the same", "spelling is a close match") says the same thing in words they can act on. */
export function VillagePicker({ value, onChange, state, language, strings }: Props) {
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState<VillageMatch[]>([])
  const [searching, setSearching] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    window.clearTimeout(timer.current)
    if (!query.trim() || value) {
      setMatches([])
      return
    }
    setSearching(true)
    timer.current = window.setTimeout(async () => {
      // The previous build cleared the debounce timer but left the in-flight request running, so
      // a slow early response could overwrite a fast later one.
      controller.current?.abort()
      const active = new AbortController()
      controller.current = active
      try {
        setMatches(await api.searchVillages(query.trim(), state, active.signal))
      } catch {
        // An abort is a superseded keystroke, not a failure; leave the older list alone.
        if (active.signal.aborted) return
        setMatches([])
      } finally {
        if (!active.signal.aborted) setSearching(false)
      }
    }, 220)
    return () => {
      window.clearTimeout(timer.current)
      controller.current?.abort()
    }
  }, [query, state, value])

  if (value) {
    return (
      <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
        <div className="ux4g-d-flex ux4g-ai-center ux4g-jc-between ux4g-gap-x-m">
          <span className="ux4g-input-chip ux4g-input-chip-md">
            <span className="ux4g-icon-outlined" aria-hidden="true">
              check_circle
            </span>
            <span className="ux4g-label-l-strong">
              {language === 'hi' && value.name_hi ? value.name_hi : value.name}
            </span>
          </span>
          <button
            type="button"
            className="ux4g-btn ux4g-btn-text-primary ux4g-btn-md"
            onClick={() => {
              onChange(null)
              setQuery('')
            }}
          >
            {strings.change}
          </button>
        </div>
        <p className="ux4g-body-m-default ux4g-text-neutral-secondary">
          {value.block} · {value.district} · {value.state}
        </p>
      </div>
    )
  }

  const noResults = !searching && query.trim() !== '' && matches.length === 0

  return (
    <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
      <div className="ux4g-d-flex ux4g-ai-end ux4g-gap-x-s ux4g-flex-wrap">
        <div className="ux4g-search-container ux4g-flex-fill">
          <label className="ux4g-label-l-strong ux4g-mb-xs" htmlFor="village">
            {strings.village}
          </label>
          <div className="ux4g-search ux4g-search-lg">
            <span className="ux4g-icon-outlined ux4g-search-leading-icon" aria-hidden="true">
              search
            </span>
            <input
              id="village"
              className="ux4g-search-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={strings.villagePlaceholder}
              autoComplete="off"
            />
            {query && (
              <div className="ux4g-search-actions">
                <button
                  type="button"
                  className="ux4g-search-action-btn ux4g-search-clear"
                  aria-label={strings.change}
                  onClick={() => setQuery('')}
                >
                  <span className="ux4g-icon-outlined" aria-hidden="true">
                    close
                  </span>
                </button>
              </div>
            )}
          </div>
        </div>
        {/* Kept outside the field, and labelled. The canonical Search puts voice input inside
            `ux4g-search-actions` as a bare icon; for a reader who cannot type comfortably this is
            the most important control on the screen, and it should say what it does. */}
        <MicButton onResult={setQuery} language={language} strings={strings} />
      </div>

      {searching && (
        <p className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-s ux4g-body-m-default" role="status">
          <span className="ux4g-spinner ux4g-spinner-sm" aria-hidden="true" />
          {strings.searching}
        </p>
      )}

      {matches.length > 0 && (
        <div>
          <p className="ux4g-label-l-strong ux4g-mb-s">{strings.confirm}</p>
          <ul className="ux4g-list ux4g-list-default ux4g-list-l">
            {matches.map((m, i) => (
              <li className="ux4g-list-item" key={m.shrid}>
                <button className="ux4g-list-item-row" type="button" onClick={() => onChange(m)}>
                  <span className="ux4g-list-item-start">
                    <span className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
                      <span className="ux4g-label-l-strong">
                        {m.name}
                        {m.name_hi ? ` · ${m.name_hi}` : ''}
                      </span>
                      <span className="ux4g-body-m-default ux4g-text-neutral-secondary">
                        {m.block} · {m.district}
                      </span>
                      <span className="ux4g-body-s-default ux4g-text-neutral-tertiary">
                        {m.reason}
                      </span>
                    </span>
                  </span>
                  <span className="ux4g-list-item-end">
                    <span
                      className={
                        i === 0
                          ? 'ux4g-tag-tonal-success ux4g-tag-s'
                          : 'ux4g-tag-tonal-neutral ux4g-tag-s'
                      }
                    >
                      {i === 0 ? strings.bestMatch : strings.possibleMatch}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {noResults && (
        <div className="ux4g-empty-state">
          <span
            className="ux4g-icon-outlined ux4g-empty-state-icon ux4g-text-primary"
            aria-hidden="true"
          >
            search_off
          </span>
          <div className="ux4g-empty-state-content">
            <h3 className="ux4g-title-s-strong">{strings.noVillageTitle}</h3>
            <p className="ux4g-body-m-default">{strings.noVillageBody}</p>
          </div>
        </div>
      )}
    </div>
  )
}
