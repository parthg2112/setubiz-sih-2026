import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { api, type FinanceResult } from '../api'
import { inr, isUnboundedDscr, ratio, type Strings } from '../format'

interface Props {
  margin: number
  category: string
  baseUnits: number
  unitLabel: string
  unitRange: [number, number]
  unitStep: number
  strings: Strings
}

const DEBOUNCE_MS = 200

/** Change an input, watch the finance recompute.
 *
 *  Only `/finance/structure` is called: the village lookup and the two estimators do not depend
 *  on any of these inputs and are comparatively slow, so re-running the whole advisory would make
 *  a slider feel broken.
 *
 *  Every slider is paired with a plain number field. On a low-end phone a slider is hard to land
 *  precisely, and this reader is often typing on a cracked screen in sunlight.
 */
export function WhatIf({
  margin,
  category,
  baseUnits,
  unitLabel,
  unitRange,
  unitStep,
  strings,
}: Props) {
  const [savings, setSavings] = useState(margin)
  const [units, setUnits] = useState(baseUnits)
  const [revenuePct, setRevenuePct] = useState(0)

  const [result, setResult] = useState<FinanceResult | null>(null)
  const [pending, setPending] = useState(false)
  const inFlight = useRef<AbortController | null>(null)

  const dirty = savings !== margin || units !== baseUnits || revenuePct !== 0

  useEffect(() => {
    const timer = window.setTimeout(() => {
      // Abandon any superseded request so a slow early response cannot overwrite a newer one.
      inFlight.current?.abort()
      const active = new AbortController()
      inFlight.current = active
      setPending(true)
      api
        .financeStructure(
          {
            margin: savings,
            business_category: category,
            units,
            revenue_factor: 1 + revenuePct / 100,
          },
          active.signal,
        )
        // The last good numbers stay on screen while a new request is in flight, so dragging
        // never flashes an empty panel.
        .then((r) => !active.signal.aborted && setResult(r))
        .catch(() => undefined)
        .finally(() => !active.signal.aborted && setPending(false))
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [savings, units, revenuePct, category])

  useEffect(() => () => inFlight.current?.abort(), [])

  const rs = result?.right_sizing
  const threshold = rs ? Number(rs.dscr_threshold) : 1.5
  /* A zero recommended loan reports DSCR as the 999 sentinel, because there is no debt service
     to divide by. That is the opposite of safe: it means the cash flow at these settings cannot
     service any loan at all, so the ratio is suppressed and the state reads as a failure. */
  const noLoan = !rs || Number(rs.recommended_loan) <= 0 || isUnboundedDscr(rs.recommended_min_dscr)
  const dscr = rs && !noLoan ? Number(rs.recommended_min_dscr) : null

  const state = !rs
    ? null
    : noLoan
      ? { tone: 'error', icon: 'cancel', label: strings.whatIfNoLoan }
      : dscr! < threshold
        ? { tone: 'error', icon: 'cancel', label: strings.whatIfFails }
        : dscr! < threshold + 0.25
          ? { tone: 'warning', icon: 'error', label: strings.whatIfTight }
          : { tone: 'success', icon: 'check_circle', label: strings.whatIfComfortable }

  function reset() {
    setSavings(margin)
    setUnits(baseUnits)
    setRevenuePct(0)
  }

  return (
    <section
      className="ux4g-card ux4g-card-outline ux4g-card-vertical ux4g-mt-l setubiz-no-print"
      aria-labelledby="whatif-heading"
    >
      <div className="ux4g-card-header">
        <h2 className="ux4g-heading-m-strong ux4g-card-title" id="whatif-heading">
          {strings.whatIfTitle}
        </h2>
        {/* The reader must be able to tell a hypothetical from their own answer. */}
        <p className="ux4g-body-l-default ux4g-card-sub-title setubiz-measure">
          {dirty ? strings.whatIfChanged : strings.whatIfYourAnswer}
        </p>
      </div>

      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-l">
        <Control
          id="whatif-savings"
          label={strings.savings}
          value={savings}
          min={5000}
          max={500000}
          step={5000}
          format={inr}
          onChange={setSavings}
        />
        <Control
          id="whatif-units"
          label={`${strings.whatIfUnitSize} (${unitLabel})`}
          value={units}
          min={unitRange[0]}
          max={unitRange[1]}
          step={unitStep}
          format={(v) => `${v} ${unitLabel}`}
          onChange={setUnits}
        />
        <Control
          id="whatif-revenue"
          label={strings.whatIfRevenue}
          value={revenuePct}
          min={-40}
          max={40}
          step={5}
          format={(v) => `${v > 0 ? '+' : ''}${v}%`}
          onChange={setRevenuePct}
        />

        <div className="ux4g-divider-horizontal" />

        <dl
          className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-4 ux4g-gap-m"
          aria-live="polite"
          aria-busy={pending}
        >
          <Figure label={strings.sizesCost} value={rs ? inr(rs.required_capital) : '—'} />
          <Figure label={strings.recommended} value={rs ? inr(rs.recommended_loan) : '—'} />
          <Figure
            label={strings.sizesPerQuarter}
            value={
              result?.schedules.recommended_loan
                ? inr(result.schedules.recommended_loan.instalment)
                : '—'
            }
          />
          <div>
            <dt className="ux4g-body-s-default ux4g-text-neutral-tertiary">
              {strings.dscrGloss}
            </dt>
            <dd className="ux4g-title-m-strong setubiz-tabular ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs">
              {dscr === null ? '—' : ratio(rs!.recommended_min_dscr)}
              {state && (
                <span className={`${'ux4g-tag-tonal-' + state.tone} ux4g-tag-s`}>
                  <span className="ux4g-icon-outlined" aria-hidden="true">
                    {state.icon}
                  </span>
                  {state.label}
                </span>
              )}
            </dd>
          </div>
        </dl>

        <div>
          <button
            type="button"
            className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
            onClick={reset}
            disabled={!dirty}
          >
            {strings.whatIfReset}
          </button>
        </div>
      </div>
    </section>
  )
}

function Control({
  id,
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
}: {
  id: string
  label: string
  value: number
  min: number
  max: number
  step: number
  format: (v: number) => string
  onChange: (v: number) => void
}) {
  const pct = ((value - min) / (max - min)) * 100
  const clamp = (v: number) => Math.min(max, Math.max(min, v))

  return (
    <div className="ux4g-slider-field ux4g-slider-md">
      <div className="ux4g-slider-label-row">
        <label className="ux4g-slider-label" htmlFor={id}>
          {label}
        </label>
        <span className="ux4g-slider-range-box setubiz-tabular">{format(value)}</span>
      </div>

      <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-m ux4g-flex-wrap">
        <div className="ux4g-slider ux4g-slider-md ux4g-flex-fill">
          <input
            type="range"
            className="ux4g-slider-input"
            id={id}
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
          />
          <div className="ux4g-slider-track">
            <div className="ux4g-slider-fill" style={{ width: `${pct}%` } as CSSProperties} />
            <div className="ux4g-slider-thumb" style={{ left: `${pct}%` } as CSSProperties} />
          </div>
        </div>

        {/* A slider is hard to land precisely on a small screen, so the same value is typeable.
            The visible label belongs to the slider; repeating it here would read as two separate
            controls, so this one carries an accessible name instead. */}
        <div className="ux4g-input-container ux4g-input-md ux4g-wpx-144">
          <div className="ux4g-input">
            <input
              id={`${id}-number`}
              className="ux4g-input-input setubiz-tabular"
              type="number"
              inputMode="numeric"
              aria-label={label}
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(e) => onChange(clamp(Number(e.target.value)))}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="ux4g-body-s-default ux4g-text-neutral-tertiary">{label}</dt>
      <dd className="ux4g-title-m-strong setubiz-tabular">{value}</dd>
    </div>
  )
}
