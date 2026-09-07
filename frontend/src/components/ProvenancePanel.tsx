import { useMemo, useState } from 'react'
import type { Facts } from '../types'

interface Props {
  facts: Facts
  open: boolean
  onClose: () => void
  language: 'en' | 'hi'
  closeLabel: string
}

/** The judge-Q&A moment: every number on screen, and exactly which source produced it. */
export function ProvenancePanel({ facts, open, onClose, language, closeLabel }: Props) {
  const [query, setQuery] = useState('')
  const sourceById = useMemo(
    () => Object.fromEntries(facts.sources.map((s) => [s.id, s])),
    [facts.sources],
  )

  const entries = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return Object.entries(facts.numeric_index)
      .filter(([key, value]) => !needle || key.includes(needle) || String(value).includes(needle))
      .sort(([a], [b]) => a.localeCompare(b))
  }, [facts.numeric_index, query])

  if (!open) return null

  return (
    <div className="no-print fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label={closeLabel}
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />
      <aside
        className="relative flex h-full w-full max-w-xl flex-col bg-surface shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <header className="flex items-start justify-between gap-4 border-b border-hairline p-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">
              {language === 'en' ? 'Data provenance' : 'आँकड़ों का स्रोत'}
            </h2>
            <p className="mt-0.5 text-xs text-ink-2">
              {entries.length}{' '}
              {language === 'en'
                ? 'computed figures. Nothing here was written by a language model.'
                : 'गणना किए गए आँकड़े। इनमें से कोई भी भाषा मॉडल ने नहीं लिखा।'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-hairline px-3 py-1.5 text-sm text-ink-2 hover:text-ink"
          >
            {closeLabel}
          </button>
        </header>

        <div className="border-b border-hairline p-4">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={language === 'en' ? 'Filter by name or value…' : 'नाम या मान से खोजें…'}
            className="w-full rounded-lg border border-hairline bg-page px-3 py-2 text-sm text-ink outline-none focus:border-accent"
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          <table className="w-full border-collapse text-sm">
            <tbody>
              {entries.map(([key, value]) => (
                <tr key={key} className="border-b border-hairline align-top">
                  <td className="w-1/2 px-4 py-2">
                    <code className="text-xs text-ink-2">{key}</code>
                    <div className="tabular font-medium text-ink">{value}</div>
                  </td>
                  <td className="px-4 py-2">
                    <ul className="space-y-1">
                      {(facts.provenance[key] ?? []).map((id) => {
                        const source = sourceById[id]
                        if (!source) return null
                        return (
                          <li key={id} className="text-xs leading-snug">
                            {source.url ? (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-accent underline underline-offset-2"
                              >
                                {source.title}
                              </a>
                            ) : (
                              <span className="text-ink-2">{source.title}</span>
                            )}
                            {source.synthetic && (
                              <span
                                className="ml-1.5 rounded px-1 py-px text-[10px] font-medium"
                                style={{
                                  background:
                                    'color-mix(in srgb, var(--status-warning) 25%, transparent)',
                                  color: 'var(--text-primary)',
                                }}
                              >
                                {language === 'en' ? 'sample' : 'नमूना'}
                              </span>
                            )}
                          </li>
                        )
                      })}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </aside>
    </div>
  )
}
