import { useId, useState } from 'react'
import { ratio } from '../format'
import { SERIES } from '../theme'
import type { DscrYear, StressScenario } from '../types'

interface Props {
  base: DscrYear[]
  scenarios: StressScenario[]
  threshold: string
  stressFloor: string
  language: 'en' | 'hi'
}


const PAD = { top: 16, right: 16, bottom: 28, left: 40 }
const W = 560
const H = 240

/** DSCR by loan year: base case plus the two stress scenarios. Lines because the reading is
 *  change across the tenure. Three series — the count the palette validates all-pairs. */
export function DscrChart({ base, scenarios, threshold, stressFloor, language }: Props) {
  const clipId = useId()
  const [hover, setHover] = useState<number | null>(null)

  const series = [
    { label: language === 'en' ? 'Base case' : 'सामान्य स्थिति', points: base.map((r) => Number(r.dscr)) },
    ...scenarios.map((s) => ({
      label: s.label.replace('revenue -', language === 'en' ? 'revenue −' : 'आय −'),
      points: s.series.map((p) => Number(p.dscr)),
    })),
  ].slice(0, 3)

  const years = base.map((r) => r.year)
  if (!years.length) return null

  // A capitalized-moratorium year has no debt service, so DSCR is sentinel-high. Clamp the scale
  // to something readable rather than letting one year flatten the rest.
  const values = series.flatMap((s) => s.points).filter((v) => v < 50)
  const yMax = Math.max(Math.ceil(Math.max(...values, Number(threshold)) + 0.5), 2)

  const x = (year: number) =>
    PAD.left + ((year - years[0]) / Math.max(years.length - 1, 1)) * (W - PAD.left - PAD.right)
  // Clamped to [0, yMax]: a stressed year can have a negative operating surplus, and an unclamped
  // point would render below the axis on top of the tick labels. It sits on the zero baseline
  // instead, and the legend reports the real figure.
  const y = (value: number) =>
    PAD.top + (1 - Math.min(Math.max(value, 0), yMax) / yMax) * (H - PAD.top - PAD.bottom)

  const ticks = Array.from({ length: yMax + 1 }, (_, i) => i)

  return (
    <figure className="setubiz-print-block">
      <div className="setubiz-scroll-x">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="ux4g-w-100"
          role="img"
          aria-label={
            language === 'en'
              ? 'Debt service coverage ratio by loan year, base case and stress scenarios'
              : 'ऋण वर्ष के अनुसार डीएससीआर, सामान्य एवं दबाव परिदृश्य'
          }
          onMouseLeave={() => setHover(null)}
        >
          <defs>
            {/* Inset by a marker radius so the first and last points are not sliced in half. */}
            <clipPath id={clipId}>
              <rect x={PAD.left - 8} y={0} width={W - PAD.left - PAD.right + 16} height={H} />
            </clipPath>
          </defs>

          {ticks.map((t) => (
            <g key={t}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(t)}
                y2={y(t)}
                stroke="var(--ux4g-border-color-neutral-default)"
                strokeWidth={1}
              />
              <text
                x={PAD.left - 8}
                y={y(t) + 4}
                textAnchor="end"
                className="setubiz-tabular"
                fill="var(--ux4g-text-neutral-tertiary)"
                fontSize={11}
              >
                {t}
              </text>
            </g>
          ))}

          {/* The appraisal norm and the stress floor are reference rules, not series. */}
          <ReferenceRule
            y={y(Number(threshold))}
            label={`${language === 'en' ? 'norm' : 'मानक'} ${ratio(threshold)}`}
          />
          <ReferenceRule
            y={y(Number(stressFloor))}
            label={`${language === 'en' ? 'floor' : 'न्यूनतम'} ${ratio(stressFloor)}`}
            dim
          />

          <g clipPath={`url(#${clipId})`}>
            {series.map((s, i) => (
              <g key={s.label}>
                <path
                  d={s.points
                    .map((v, idx) => `${idx ? 'L' : 'M'}${x(years[idx])},${y(v)}`)
                    .join(' ')}
                  fill="none"
                  stroke={SERIES[i]}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {s.points.map((v, idx) => (
                  <circle
                    key={idx}
                    cx={x(years[idx])}
                    cy={y(v)}
                    r={hover === years[idx] ? 5.5 : 4}
                    fill={SERIES[i]}
                    stroke="var(--ux4g-bg-neutral-elevated)"
                    strokeWidth={2}
                  />
                ))}
              </g>
            ))}
          </g>

          {years.map((year) => (
            <g key={year}>
              <text
                x={x(year)}
                y={H - 8}
                textAnchor="middle"
                className="setubiz-tabular"
                fill="var(--ux4g-text-neutral-tertiary)"
                fontSize={11}
              >
                {language === 'en' ? `Y${year}` : `व${year}`}
              </text>
              {hover === year && (
                <line
                  x1={x(year)}
                  x2={x(year)}
                  y1={PAD.top}
                  y2={H - PAD.bottom}
                  stroke="var(--setubiz-chart-axis)"
                  strokeWidth={1}
                />
              )}
              {/* Hit target is far wider than the mark. Pointer-only and aria-hidden: it used to
                  carry tabIndex={0} alongside role="presentation", which put a stop in the tab
                  order that screen readers were simultaneously told to ignore. The chart's own
                  role="img" and aria-label carry the reading, and every plotted figure also
                  appears in the schedule table below. */}
              <rect
                x={x(year) - 18}
                y={0}
                width={36}
                height={H}
                fill="transparent"
                aria-hidden="true"
                onMouseEnter={() => setHover(year)}
                onMouseLeave={() => setHover(null)}
              />
            </g>
          ))}
        </svg>
      </div>

      <figcaption className="ux4g-body-s-default ux4g-d-flex ux4g-flex-wrap ux4g-ai-center ux4g-gap-m ux4g-mt-s ux4g-text-neutral-secondary">
        {series.map((s, i) => {
          const worst = Math.min(...s.points)
          return (
            <span key={s.label} className="ux4g-d-inline-flex ux4g-ai-center ux4g-gap-x-xs">
              {/* Legend swatch: chart furniture, sized here because it must match the 2px stroke
                  weight of the line it stands for, which is not a value the token scale carries. */}
              <span
                aria-hidden
                className="ux4g-d-inline-block"
                style={{ background: SERIES[i], width: 16, height: 2, borderRadius: 999 }}
              />
              {s.label}
              {hover !== null ? (
                <span className="ux4g-label-m-strong setubiz-tabular">
                  {ratio(s.points[years.indexOf(hover)] ?? 0)}
                </span>
              ) : (
                worst <= 0 && (
                  <span className="ux4g-label-m-strong" style={{ color: 'var(--ux4g-text-status-error)' }}>
                    {language === 'en' ? 'no surplus to service debt' : 'चुकाने योग्य अधिशेष नहीं'}
                  </span>
                )
              )}
            </span>
          )
        })}
      </figcaption>
    </figure>
  )
}

function ReferenceRule({ y, label, dim }: { y: number; label: string; dim?: boolean }) {
  return (
    <g>
      <line
        x1={PAD.left}
        x2={W - PAD.right}
        y1={y}
        y2={y}
        stroke="var(--setubiz-chart-axis)"
        strokeWidth={1}
        strokeDasharray={dim ? '2 4' : '5 4'}
      />
      <text x={W - PAD.right} y={y - 5} textAnchor="end" fill="var(--ux4g-text-neutral-tertiary)" fontSize={10}>
        {label}
      </text>
    </g>
  )
}
