import { useMemo, useRef, useState } from 'react'
import type { Facts, Language } from '../types'
import { useDialog } from '../useDialog'

interface Props {
  facts: Facts
  open: boolean
  onClose: () => void
  language: Language
  closeLabel: string
  title: string
}

/** Every number on screen, and exactly which published source produced it.
 *
 *  This is the panel that answers "did a language model make this up?" — so it says, in the
 *  reader's language, that nothing in it was written by one. */
export function ProvenancePanel({ facts, open, onClose, language, closeLabel, title }: Props) {
  const [query, setQuery] = useState('')
  const panel = useRef<HTMLElement | null>(null)
  useDialog(open, panel, onClose)

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
    <div className="setubiz-no-print">
      <div className="ux4g-drawer-overlay ux4g-drawer-open" onClick={onClose} aria-hidden="true" />
      <aside
        ref={panel}
        className="ux4g-drawer ux4g-drawer-right ux4g-drawer-open"
        role="dialog"
        aria-modal="true"
        aria-labelledby="provenance-title"
      >
        <header className="ux4g-drawer-header">
          <div className="ux4g-drawer-title-group">
            <h2 className="ux4g-drawer-title" id="provenance-title">
              {title}
            </h2>
            <p className="ux4g-drawer-subtitle">
              {entries.length}{' '}
              {language === 'en'
                ? 'computed figures. Nothing here was written by a language model.'
                : 'गणना किए गए आँकड़े। इनमें से कोई भी भाषा मॉडल ने नहीं लिखा।'}
            </p>
          </div>
          <button
            type="button"
            className="ux4g-drawer-close"
            onClick={onClose}
            aria-label={closeLabel}
          >
            <span className="ux4g-icon-outlined" aria-hidden="true">
              close
            </span>
          </button>
        </header>

        <div className="ux4g-drawer-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
          <div className="ux4g-search-container">
            <div className="ux4g-search ux4g-search-s">
              <span className="ux4g-icon-outlined ux4g-search-leading-icon" aria-hidden="true">
                search
              </span>
              <input
                className="ux4g-search-input"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label={title}
                placeholder={
                  language === 'en' ? 'Filter by name or value…' : 'नाम या मान से खोजें…'
                }
              />
            </div>
          </div>

          <div className="ux4g-table-responsive">
            <table className="ux4g-table ux4g-table-s">
              <tbody>
                {entries.map(([key, value]) => (
                  <tr key={key}>
                    <th scope="row">
                      <span className="ux4g-body-s-default ux4g-text-neutral-tertiary">{key}</span>
                      <br />
                      <span className="ux4g-label-l-strong setubiz-tabular">{value}</span>
                    </th>
                    <td>
                      <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
                        {(facts.provenance[key] ?? []).map((id) => {
                          const source = sourceById[id]
                          if (!source) return null
                          return (
                            <li
                              className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs ux4g-flex-wrap"
                              key={id}
                            >
                              {source.url ? (
                                <a
                                  className="ux4g-text-link-sm"
                                  href={source.url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {source.title}
                                </a>
                              ) : (
                                <span className="ux4g-body-s-default">{source.title}</span>
                              )}
                              {/* Per-source, not a page-wide banner: the backend flags each file
                                  independently, so one sample source among real ones is visible. */}
                              <span
                                className={
                                  source.synthetic
                                    ? 'ux4g-tag-tonal-warning ux4g-tag-s'
                                    : 'ux4g-tag-tonal-success ux4g-tag-s'
                                }
                              >
                                {source.synthetic
                                  ? language === 'en'
                                    ? 'sample'
                                    : 'नमूना'
                                  : language === 'en'
                                    ? 'official'
                                    : 'आधिकारिक'}
                              </span>
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
        </div>
      </aside>
    </div>
  )
}
