import { useState } from 'react'

interface Props {
  months: string[]
  arrivals: number[]
  commodity: string
  market: string
  peakMonth?: string
  troughMonth?: string
  language: 'en' | 'hi'
}

const PAD = { top: 14, right: 12, bottom: 26, left: 44 }
const W = 560
const H = 180

/** One series, so no legend box — the caption names it. Bars, because monthly arrivals are
 *  discrete magnitudes and the peak/trough comparison is the whole point. */
export function SeasonalityChart({
  months,
  arrivals,
  commodity,
  market,
  peakMonth,
  troughMonth,
  language,
}: Props) {
  const [hover, setHover] = useState<number | null>(null)
  if (!months.length || !arrivals.length) return null

  const yMax = Math.max(...arrivals) * 1.1
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const slot = plotW / months.length
  const barW = Math.max(slot - 2, 4) // 2px surface gap between adjacent bars

  return (
    <figure className="setubiz-print-block">
      <div className="setubiz-scroll-x">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="ux4g-w-100"
          role="img"
          aria-label={
            language === 'en'
              ? `Monthly ${commodity} arrivals at ${market}`
              : `${market} में ${commodity} की मासिक आवक`
          }
          onMouseLeave={() => setHover(null)}
        >
          {[0, 0.5, 1].map((f) => (
            <g key={f}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={PAD.top + (1 - f) * plotH}
                y2={PAD.top + (1 - f) * plotH}
                stroke="var(--ux4g-border-color-neutral-default)"
                strokeWidth={1}
              />
              <text
                x={PAD.left - 8}
                y={PAD.top + (1 - f) * plotH + 4}
                textAnchor="end"
                className="setubiz-tabular"
                fill="var(--ux4g-text-neutral-tertiary)"
                fontSize={10}
              >
                {Math.round((yMax * f) / 100) * 100}
              </text>
            </g>
          ))}

          {arrivals.map((value, i) => {
            const h = (value / yMax) * plotH
            const isExtreme = months[i] === peakMonth || months[i] === troughMonth
            return (
              <g
                key={months[i]}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                aria-hidden="true"
              >
                <rect
                  x={PAD.left + i * slot}
                  y={0}
                  width={slot}
                  height={H}
                  fill="transparent"
                />
                <rect
                  x={PAD.left + i * slot + (slot - barW) / 2}
                  y={PAD.top + plotH - h}
                  width={barW}
                  height={h}
                  rx={4}
                  fill="var(--setubiz-chart-1)"
                  opacity={hover === null || hover === i ? 1 : 0.55}
                />
                {(isExtreme || hover === i) && (
                  <text
                    x={PAD.left + i * slot + slot / 2}
                    y={PAD.top + plotH - h - 4}
                    textAnchor="middle"
                    className="setubiz-tabular"
                    fill="var(--ux4g-text-neutral-primary)"
                    fontSize={10}
                    fontWeight={600}
                  >
                    {value}
                  </text>
                )}
                <text
                  x={PAD.left + i * slot + slot / 2}
                  y={H - 8}
                  textAnchor="middle"
                  fill={isExtreme ? 'var(--ux4g-text-neutral-secondary)' : 'var(--ux4g-text-neutral-tertiary)'}
                  fontSize={10}
                  fontWeight={isExtreme ? 600 : 400}
                >
                  {months[i]}
                </text>
              </g>
            )
          })}

          <line
            x1={PAD.left}
            x2={W - PAD.right}
            y1={PAD.top + plotH}
            y2={PAD.top + plotH}
            stroke="var(--setubiz-chart-axis)"
            strokeWidth={1}
          />
        </svg>
      </div>
      <figcaption className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mt-xs">
        {language === 'en'
          ? `${commodity} arrivals at ${market}, tonnes per month`
          : `${market} में ${commodity} की आवक, टन प्रति माह`}
      </figcaption>
    </figure>
  )
}
