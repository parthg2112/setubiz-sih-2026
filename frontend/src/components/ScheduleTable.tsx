import { useState } from 'react'
import { inr, type Strings } from '../format'
import type { Language, ScheduleRow } from '../types'

interface Props {
  rows: ScheduleRow[]
  mode: string
  alternateMode: string | null
  alternateInstalment: string | null
  language: Language
  strings: Strings
}

const HEAD = {
  en: ['Qtr', 'Opening', 'Interest', 'Principal', 'Instalment', 'Closing'],
  hi: ['तिमाही', 'प्रारंभिक शेष', 'ब्याज', 'मूलधन', 'किस्त', 'अंतिम शेष'],
}

export function ScheduleTable({
  rows,
  mode,
  alternateMode,
  alternateInstalment,
  language,
  strings,
}: Props) {
  const [expanded, setExpanded] = useState(false)
  if (!rows.length) return null
  const shown = expanded ? rows : rows.slice(0, 6)

  return (
    <div className="setubiz-print-block ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
      <p className="ux4g-body-m-default ux4g-text-neutral-secondary setubiz-measure">
        {language === 'en' ? 'Moratorium interest: ' : 'अधिस्थगन ब्याज: '}
        <strong>
          {mode === 'serviced'
            ? language === 'en'
              ? 'paid each quarter'
              : 'हर तिमाही चुकाया'
            : language === 'en'
              ? 'added to principal'
              : 'मूलधन में जोड़ा'}
        </strong>
      </p>

      {/* The alternate moratorium treatment is not a question the reader is asked during the form
          — it is jargon they have no basis to answer. It is shown here instead, already computed,
          as a comparison they can take to the bank. */}
      {alternateInstalment && (
        <p className="ux4g-body-m-default ux4g-text-neutral-secondary setubiz-measure">
          {strings.moratoriumAlt}{' '}
          <span className="setubiz-tabular">{inr(alternateInstalment)}</span>
          {language === 'en' ? ` a quarter (${alternateMode})` : ' प्रति तिमाही'}
        </p>
      )}

      <div className="ux4g-table-responsive">
        <table className="ux4g-table ux4g-table-m ux4g-table-zebra-rows ux4g-table-rounded">
          <thead>
            <tr>
              {HEAD[language].map((h) => (
                <th key={h} scope="col">
                  <span className="ux4g-table-th-content">{h}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="setubiz-tabular">
            {shown.map((row) => (
              <tr key={row.quarter}>
                <th scope="row">
                  {row.quarter}
                  {row.phase === 'moratorium' && (
                    <span className="ux4g-tag-tonal-warning ux4g-tag-s ux4g-ml-xs">
                      {language === 'en' ? 'moratorium' : 'अधिस्थगन'}
                    </span>
                  )}
                </th>
                <td>{inr(row.opening)}</td>
                <td>{inr(row.interest)}</td>
                <td>{inr(row.principal)}</td>
                <td>
                  <strong>{inr(row.instalment)}</strong>
                </td>
                <td>{inr(row.closing)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length > 6 && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="ux4g-btn ux4g-btn-text-primary ux4g-btn-lg setubiz-no-print"
        >
          {expanded ? strings.hideSchedule : `${strings.showSchedule} (${rows.length})`}
        </button>
      )}
    </div>
  )
}
