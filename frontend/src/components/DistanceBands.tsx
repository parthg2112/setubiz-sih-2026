import type { VillageDot } from '../types'

interface Props {
  villages: VillageDot[]
  radiusKm: number
  language: 'en' | 'hi'
}

/** Households by distance band.
 *
 *  A catchment is not uniform: the first couple of kilometres hold most of the custom. Four bars
 *  say that at a glance, where the chip wall said nothing. Band edges are radius/4 so they track
 *  the rings on the catchment map beside them. */
export function DistanceBands({ villages, radiusKm, language }: Props) {
  const step = radiusKm / 4
  const bands = [0, 1, 2, 3].map((i) => {
    const from = step * i
    const to = step * (i + 1)
    const inBand = villages.filter((v) => v.distance_km > (i === 0 ? -1 : from) && v.distance_km <= to)
    return {
      label: `${from}-${to}`,
      households: inBand.reduce((sum, v) => sum + v.households_2011, 0),
      count: inBand.length,
    }
  })
  const max = Math.max(1, ...bands.map((b) => b.households))
  const heading =
    language === 'hi' ? 'दूरी के अनुसार परिवार' : 'Households by distance from the village'

  return (
    <div role="img" aria-label={`${heading}: ${bands.map((b) => `${b.label} km, ${b.households}`).join(', ')}`}>
      <p className="ux4g-label-l-strong ux4g-mb-s">{heading}</p>
      <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
        {bands.map((b) => (
          <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-s" key={b.label}>
            <span className="setubiz-band-label setubiz-tabular">{b.label} km</span>
            <span className="setubiz-band-track">
              <span
                className="setubiz-band-fill"
                style={{ width: `${(b.households / max) * 100}%` }}
              />
            </span>
            <span className="ux4g-body-s-default setubiz-tabular ux4g-text-neutral-secondary">
              {b.households.toLocaleString(language === 'hi' ? 'hi-IN' : 'en-IN')} · {b.count}{' '}
              {language === 'hi' ? 'गाँव' : 'villages'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

interface SegmentProps {
  segments: { label: string; share: string; households: number }[]
  language: 'en' | 'hi'
}

/** The catchment's purchasing power in one bar.
 *
 *  HCES income fractiles, drawn as a single stacked strip: who lives here, from the bottom 30%
 *  to the top 10%, and roughly how many households each band holds. Data ships in the section
 *  payload; nothing is recomputed on the client. */
export function IncomeSegments({ segments, language }: SegmentProps) {
  if (!segments.length) return null
  const total = segments.reduce((sum, s) => sum + s.households, 0)
  const tones = [
    'var(--setubiz-chart-4)',
    'var(--setubiz-chart-1)',
    'var(--setubiz-chart-2)',
    'var(--setubiz-chart-5)',
  ]
  const heading = language === 'hi' ? 'परिवार आय वर्ग अनुसार' : 'Households by income band (HCES)'
  return (
    <div
      role="img"
      aria-label={`${heading}: ${segments
        .map((s) => `${s.label} ${Math.round(Number(s.share) * 100)}%`)
        .join(', ')}`}
    >
      <p className="ux4g-label-l-strong ux4g-mb-s">{heading}</p>
      <div className="setubiz-income-bar">
        {segments.map((s, i) => (
          <span
            key={s.label}
            className="setubiz-income-seg"
            style={{ width: `${(s.households / total) * 100}%`, background: tones[i % tones.length] }}
            title={`${s.label} · ${s.households.toLocaleString(language === 'hi' ? 'hi-IN' : 'en-IN')}`}
          />
        ))}
      </div>
      <div className="ux4g-body-s-default ux4g-d-flex ux4g-gap-x-m ux4g-flex-wrap ux4g-mt-xs ux4g-text-neutral-secondary">
        {segments.map((s, i) => (
          <span className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs" key={s.label}>
            <span
              className="setubiz-dot"
              style={{ background: tones[i % tones.length] }}
              aria-hidden="true"
            />
            {s.label} · {Math.round(Number(s.share) * 100)}% ·{' '}
            <span className="setubiz-tabular">
              {s.households.toLocaleString(language === 'hi' ? 'hi-IN' : 'en-IN')}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}
