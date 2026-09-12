import { useState } from 'react'
import type { Strings } from '../format'
import type { Language, VillageDot } from '../types'

interface Props {
  centreName: string
  centre: { lat: number; lon: number }
  villages: VillageDot[]
  radiusKm: number
  language: Language
  strings: Strings
}

const SIZE = 560
const C = SIZE / 2
const R = 220

/** The catchment as a place, not a list.
 *
 *  Each village in range is a bubble at its real bearing and distance from the centre, sized by
 *  households, on distance rings the reader can count. Bubble colour is the market-reach signal:
 *  a light-to-dark blue ramp over the households scale, with the numeric legend below, so "where
 *  is the demand" reads as a shade before a single tooltip is opened. Bank villages carry a small
 *  contrasting pin instead of a colour, because one binary fact should not own the whole ramp.
 *  No map tiles and no external library: the geometry is a bearing and a ratio, drawn as SVG like
 *  the other charts, so it works offline and prints. */
export function CatchmentMap({ centreName, centre, villages, radiusKm, language, strings }: Props) {
  const [hover, setHover] = useState<VillageDot | null>(null)

  const maxHH = Math.max(1, ...villages.map((v) => v.households_2011))
  const minHH = Math.min(...villages.map((v) => v.households_2011))
  const midHH = Math.round((maxHH + minHH) / 2)
  const rings = [1, 2, 3, 4].map((i) => (radiusKm / 4) * i)

  // Equirectangular bearing: exact enough at village distances, and the plotted radius uses the
  // backend's own haversine distance so a bubble always sits on its true ring.
  const phiC = (centre.lat * Math.PI) / 180
  const position = (v: VillageDot) => {
    const dx = ((v.lon - centre.lon) * Math.PI) / 180
    const dy = ((v.lat - centre.lat) * Math.PI) / 180
    const angle = Math.atan2(dx * Math.cos(phiC), dy)
    const t = Math.min(v.distance_km / radiusKm, 1)
    return {
      x: C + t * R * Math.sin(angle),
      y: C - t * R * Math.cos(angle),
      r: 3 + 11 * Math.sqrt(v.households_2011 / maxHH),
    }
  }

  /* The shade scale. A square-root spread keeps the thin end of the catchment from collapsing
   * into one undifferentiated pale blob next to one or two giants. color-mix keeps every step on
   * the UX4G blue ramp through the theme variables, so dark mode needs no second palette. */
  const shade = (v: VillageDot) => {
    const p = Math.round(Math.sqrt(v.households_2011 / maxHH) * 100)
    return `color-mix(in srgb, var(--setubiz-map-dark) ${p}%, var(--setubiz-map-light))`
  }

  const fmt = (n: number) => n.toLocaleString(language === 'hi' ? 'hi-IN' : 'en-IN')
  const summary =
    language === 'hi'
      ? `${centreName} से ${radiusKm} किमी के दायरे में ${villages.length} गाँव, रंग गहरा होने का अर्थ अधिक परिवार। सबसे बड़े: ${[...villages]
          .sort((a, b) => b.households_2011 - a.households_2011)
          .slice(0, 3)
          .map((v) => `${v.name} (${v.households_2011} परिवार)`)
          .join(', ')}।`
      : `${villages.length} villages within ${radiusKm} km of ${centreName}; darker blue means more households. Largest: ${[...villages]
          .sort((a, b) => b.households_2011 - a.households_2011)
          .slice(0, 3)
          .map((v) => `${v.name} (${v.households_2011} households)`)
          .join(', ')}.`

  return (
    <figure className="setubiz-scroll-x setubiz-catchment-figure">
      <div className="setubiz-catchment">
        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          role="img"
          aria-label={summary}
          className="setubiz-catchment-svg"
        >
          {rings.map((km, i) => (
            <g key={km}>
              <circle
                cx={C}
                cy={C}
                r={(km / radiusKm) * R}
                fill="none"
                stroke="var(--setubiz-chart-axis)"
                strokeDasharray={i === 3 ? undefined : '3 5'}
                strokeWidth={1}
              />
              <text
                x={C + 4}
                y={C - (km / radiusKm) * R - 4}
                className="setubiz-catchment-ring-label setubiz-tabular"
              >
                {km} {strings.km}
              </text>
            </g>
          ))}

          {/* The applicant's own village: a filled marker at the centre, named. */}
          <circle cx={C} cy={C} r={5} fill="var(--setubiz-chart-1)" />
          <text x={C + 9} y={C + 4} className="setubiz-catchment-centre-label">
            {centreName}
          </text>

          {villages
            .filter((v) => v.distance_km > 0.05)
            .map((v) => {
              const p = position(v)
              return (
                <g key={v.name}>
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={p.r}
                    fill={shade(v)}
                    stroke="var(--setubiz-catchment-stroke)"
                    strokeWidth={1}
                    onMouseEnter={() => setHover(v)}
                    onMouseLeave={() => setHover(null)}
                    style={{ cursor: 'default' }}
                  />
                  {/* The binary bank fact rides on top of the ramp as a pin, never as colour. */}
                  {v.has_bank && (
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={Math.max(1.6, p.r * 0.32)}
                      fill="var(--setubiz-catchment-stroke)"
                      pointerEvents="none"
                    />
                  )}
                  <title>
                    {`${language === 'hi' && v.name_hi ? v.name_hi : v.name} · ${v.distance_km} ${strings.km} · ${v.households_2011} ${strings.statHouseholdsShort}${v.has_bank ? ` · ${strings.hasBank}` : ''}`}
                  </title>
                </g>
              )
            })}
        </svg>

        {hover && (
          <div
            className="setubiz-catchment-tip setubiz-tabular"
            role="status"
            style={{
              left: `${(position(hover).x / SIZE) * 100}%`,
              top: `${(position(hover).y / SIZE) * 100}%`,
              // Bubbles near the right edge would push the tooltip off the panel: flip it to
              // open leftward once the anchor crosses the middle.
              transform:
                position(hover).x > SIZE * 0.55
                  ? 'translate(calc(-100% - 0.75rem), -50%)'
                  : 'translate(0.75rem, -50%)',
            }}
          >
            <strong>{language === 'hi' && hover.name_hi ? hover.name_hi : hover.name}</strong>
            <br />
            {hover.distance_km} {strings.km} · {hover.households_2011}{' '}
            {strings.statHouseholdsShort}
            {hover.has_bank ? ` · ${strings.hasBank}` : ''}
          </div>
        )}
      </div>

      {/* The scale, with numbers, directly under the map: dark = more demand. Without it the
       *  ramp is decoration; with it, a shade answers "where is the market" on sight. */}
      <figcaption className="ux4g-mt-s">
        <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-m ux4g-flex-wrap">
          <span className="ux4g-label-m-strong">{strings.mapLegendTitle}</span>
          <span className="ux4g-body-s-default ux4g-d-flex ux4g-ai-center ux4g-gap-x-m ux4g-flex-wrap ux4g-text-neutral-secondary">
            <span className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs">
              <span className="setubiz-dot setubiz-pin" aria-hidden="true" />
              {strings.mapLegendBank}
            </span>
            <span className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs">
              <span aria-hidden="true">⌀</span>
              {strings.legendSize}
            </span>
          </span>
        </div>
        <div className="setubiz-map-scale ux4g-mt-xs" role="presentation">
          <div className="setubiz-map-scale-bar" />
          <div className="setubiz-map-scale-labels setubiz-tabular">
            <span>≈ {fmt(Math.round(minHH))}</span>
            <span>≈ {fmt(midHH)}</span>
            <span>≈ {fmt(Math.round(maxHH))}</span>
          </div>
        </div>
      </figcaption>
    </figure>
  )
}
