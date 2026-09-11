import type { CSSProperties } from 'react'
import type { Band, Language } from '../types'

interface Props {
  band: Band
  format: (value: string) => string
  label: string
  language: Language
}

const CONFIDENCE_LABEL = {
  en: { high: 'Fairly sure', medium: 'Roughly right', low: 'Rough guess' },
  hi: { high: 'काफी हद तक पक्का', medium: 'लगभग सही', low: 'मोटा अनुमान' },
}

/** An estimate is a range with a method, never a bare number.
 *
 *  The confidence word is deliberately plain. "Low confidence" is a statistician's phrase; "rough
 *  guess" tells a first-time borrower the same thing and tells it honestly. The method line stays
 *  verbatim from the backend — it is what an appraising officer will ask about. */
export function BandBar({ band, format, label, language }: Props) {
  const low = Number(band.low)
  const point = Number(band.point)
  const high = Number(band.high)
  const span = Math.max(high - low, 1)
  const pct = { '--ux4g-progress-value': ((point - low) / span) * 100 } as CSSProperties

  const tone =
    band.confidence === 'low'
      ? 'ux4g-tag-tonal-warning'
      : band.confidence === 'high'
        ? 'ux4g-tag-tonal-success'
        : 'ux4g-tag-tonal-info'

  return (
    <div className="ux4g-card ux4g-card-outline ux4g-card-vertical setubiz-print-block">
      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
        <div className="ux4g-d-flex ux4g-ai-center ux4g-jc-between ux4g-gap-x-s ux4g-flex-wrap">
          <h4 className="ux4g-label-l-strong">{label}</h4>
          <span className={`${tone} ux4g-tag-s`}>
            {CONFIDENCE_LABEL[language][band.confidence]}
          </span>
        </div>

        <p className="ux4g-heading-m-strong setubiz-tabular">
          {format(band.low)} – {format(band.high)}
        </p>

        {/* The bar shows where the point estimate sits inside the range, not a completion value. */}
        <div className="ux4g-progress-bar">
          <div className="ux4g-progress-bar-track">
            <div className="ux4g-progress-bar-fill" style={pct} />
          </div>
        </div>

        <p className="ux4g-body-s-default ux4g-text-neutral-tertiary">{band.method}</p>
      </div>
    </div>
  )
}
