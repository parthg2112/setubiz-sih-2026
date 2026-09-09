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
    <figure className="print-block m-0">
      <div className="overflow-x-auto max-w-[760px]">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full min-w-[420px]"
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
                stroke="var(--border)"
                strokeWidth={1}
              />
              <text
                x={PAD.left - 8}
                y={y(t) + 4}
                textAnchor="end"
                className="tabular"
                fill="var(--subtle-foreground)"
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
                    stroke="var(--card)"
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
                className="tabular"
                fill="var(--subtle-foreground)"
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
                  stroke="var(--chart-axis)"
                  strokeWidth={1}
                />
              )}
              {/* Hit target is far wider than the mark. */}
              <rect
                x={x(year) - 18}
                y={0}
                width={36}
                height={H}
                fill="transparent"
                onMouseEnter={() => setHover(year)}
                onFocus={() => setHover(year)}
                tabIndex={0}
                role="presentation"
              />
            </g>
          ))}
        </svg>
      </div>

      <figcaption className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {series.map((s, i) => {
          const worst = Math.min(...s.points)
          return (
            <span key={s.label} className="inline-flex items-center gap-1.5">
              <span
                aria-hidden
                className="inline-block h-0.5 w-4 rounded-full"
                style={{ background: SERIES[i] }}
              />
              {s.label}
              {hover !== null ? (
                <span className="tabular font-medium text-foreground">
                  {ratio(s.points[years.indexOf(hover)] ?? 0)}
                </span>
              ) : (
                worst <= 0 && (
                  <span className="font-medium" style={{ color: 'var(--destructive)' }}>
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
        stroke="var(--chart-axis)"
        strokeWidth={1}
        strokeDasharray={dim ? '2 4' : '5 4'}
      />
      <text x={W - PAD.right} y={y - 5} textAnchor="end" fill="var(--subtle-foreground)" fontSize={10}>
        {label}
      </text>
    </g>
  )
}
