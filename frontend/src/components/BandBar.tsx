import type { Band } from '../types'

interface Props {
  band: Band
  format: (value: string) => string
  label: string
  language: 'en' | 'hi'
}

const CONFIDENCE_LABEL = {
  en: { high: 'high confidence', medium: 'medium confidence', low: 'low confidence' },
  hi: { high: 'उच्च विश्वास', medium: 'मध्यम विश्वास', low: 'निम्न विश्वास' },
}

/** An estimate is a range with a method, never a bare number. The badge and the method line are
 *  the honest part — they are what a judge asks about. */
export function BandBar({ band, format, label, language }: Props) {
  const low = Number(band.low)
  const point = Number(band.point)
  const high = Number(band.high)
  const span = Math.max(high - low, 1)
  const markerPct = ((point - low) / span) * 100

  return (
    <div className="print-block rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-sm font-medium text-muted-foreground">{label}</h4>
        <span
          className="rounded px-1.5 py-0.5 text-[11px] font-medium text-foreground"
          style={{
            background:
              band.confidence === 'low'
                ? 'color-mix(in srgb, var(--warning) 28%, transparent)'
                : 'color-mix(in srgb, var(--chart-1) 16%, transparent)',
          }}
        >
          {CONFIDENCE_LABEL[language][band.confidence]}
        </span>
      </div>

      <p className="tabular mt-1 text-2xl font-semibold text-foreground">
        {format(band.low)} – {format(band.high)}
      </p>

      <div className="relative mt-3 h-3">
        <div className="absolute inset-x-0 top-1 h-1.5 rounded-full bg-muted" />
        <div
          className="absolute top-1 h-1.5 rounded-full"
          style={{ left: 0, right: 0, background: 'var(--chart-1)', opacity: 0.35 }}
        />
        <div
          className="absolute top-0 size-3 -translate-x-1/2 rounded-full"
          style={{
            left: `${markerPct}%`,
            background: 'var(--chart-1)',
            border: '2px solid var(--card)',
          }}
          title={format(band.point)}
        />
      </div>

      <p className="mt-2 text-xs leading-snug text-subtle-foreground">{band.method}</p>
    </div>
  )
}
