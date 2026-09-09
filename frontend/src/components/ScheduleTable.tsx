import { useState } from 'react'
import { inr } from '../format'
import type { ScheduleRow } from '../types'

interface Props {
  rows: ScheduleRow[]
  mode: string
  alternateMode: string | null
  alternateInstalment: string | null
  language: 'en' | 'hi'
  strings: { schedule: string; showSchedule: string; hideSchedule: string }
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
    <div className="print-block">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-sm font-semibold text-foreground">{strings.schedule}</h4>
        <p className="text-xs text-muted-foreground">
          {language === 'en' ? 'Moratorium interest: ' : 'अधिस्थगन ब्याज: '}
          <strong className="font-medium">
            {mode === 'serviced'
              ? language === 'en'
                ? 'paid each quarter'
                : 'हर तिमाही चुकाया'
              : language === 'en'
                ? 'added to principal'
                : 'मूलधन में जोड़ा'}
          </strong>
          {alternateInstalment && (
            <>
              {' · '}
              {language === 'en' ? 'the other treatment costs ' : 'दूसरे तरीके में किस्त '}
              <span className="tabular">{inr(alternateInstalment)}</span>
              {language === 'en' ? ` a quarter (${alternateMode})` : ' प्रति तिमाही'}
            </>
          )}
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[560px] border-collapse text-right text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-subtle-foreground">
              {HEAD[language].map((h, i) => (
                <th key={h} className={`px-3 py-2 font-medium ${i === 0 ? 'text-left' : ''}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="tabular">
            {shown.map((row) => (
              <tr
                key={row.quarter}
                className="border-b border-border last:border-0"
                style={
                  row.phase === 'moratorium'
                    ? { background: 'color-mix(in srgb, var(--chart-2) 8%, transparent)' }
                    : undefined
                }
              >
                <td className="px-3 py-1.5 text-left text-muted-foreground">
                  {row.quarter}
                  {row.phase === 'moratorium' && (
                    <span className="ml-1 text-[10px] uppercase tracking-wide text-subtle-foreground">
                      {language === 'en' ? 'mor.' : 'अधि.'}
                    </span>
                  )}
                </td>
                <td className="px-3 py-1.5 text-muted-foreground">{inr(row.opening)}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{inr(row.interest)}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{inr(row.principal)}</td>
                <td className="px-3 py-1.5 font-medium text-foreground">{inr(row.instalment)}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{inr(row.closing)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length > 6 && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="no-print mt-2 text-sm font-medium text-primary underline underline-offset-2"
        >
          {expanded ? strings.hideSchedule : `${strings.showSchedule} (${rows.length})`}
        </button>
      )}
    </div>
  )
}
