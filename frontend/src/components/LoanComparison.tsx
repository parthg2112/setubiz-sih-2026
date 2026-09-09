import { BINDING_LABEL, inr, ratio } from '../format'
import type { Language } from '../types'

interface Props {
  maxLoan: string
  recommendedLoan: string
  headroom: string
  requiredCapital: string
  debtNeed: string
  binding: string
  maxMinDscr: string
  recommendedMinDscr: string
  dscrThreshold: string
  language: Language
  strings: { maxLoan: string; recommended: string; difference: string; worstYear: string }
}

/** The headline comparison. Two bars, semantic status colors (not categorical series colors),
 *  each with an icon and a written label — status color never carries meaning alone. */
export function LoanComparison({
  maxLoan,
  recommendedLoan,
  headroom,
  requiredCapital,
  debtNeed,
  binding,
  maxMinDscr,
  recommendedMinDscr,
  dscrThreshold,
  language,
  strings,
}: Props) {
  const max = Number(maxLoan)
  const recommended = Number(recommendedLoan)
  const need = Number(debtNeed)
  const scale = Math.max(max, need, 1)
  const bindingLabel = BINDING_LABEL[binding]?.[language] ?? binding

  return (
    <section className="print-block rounded-xl border border-border bg-card p-5 sm:p-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <Figure
          tone="critical"
          icon="!"
          label={strings.maxLoan}
          amount={maxLoan}
          widthPct={(max / scale) * 100}
          footnote={`${strings.worstYear} ${ratio(maxMinDscr)} · ${language === 'en' ? 'norm' : 'मानक'} ${ratio(dscrThreshold)}`}
          failing={Number(maxMinDscr) < Number(dscrThreshold)}
        />
        <Figure
          tone="good"
          icon="✓"
          label={strings.recommended}
          amount={recommendedLoan}
          widthPct={(recommended / scale) * 100}
          footnote={`${strings.worstYear} ${ratio(recommendedMinDscr)} · ${bindingLabel}`}
          failing={false}
        />
      </div>

      <dl className="mt-5 grid gap-x-6 gap-y-2 border-t border-border pt-4 text-sm sm:grid-cols-3">
        <Stat label={strings.difference} value={inr(headroom)} emphasis />
        <Stat
          label={language === 'en' ? 'The unit actually costs' : 'इकाई की वास्तविक लागत'}
          value={inr(requiredCapital)}
        />
        <Stat
          label={language === 'en' ? 'Debt actually needed' : 'वास्तव में आवश्यक ऋण'}
          value={inr(debtNeed)}
        />
      </dl>
    </section>
  )
}

function Figure({
  tone,
  icon,
  label,
  amount,
  widthPct,
  footnote,
  failing,
}: {
  tone: 'critical' | 'good'
  icon: string
  label: string
  amount: string
  widthPct: number
  footnote: string
  failing: boolean
}) {
  const color = tone === 'critical' ? 'var(--destructive)' : 'var(--success)'
  return (
    <div>
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <span
          aria-hidden
          className="grid size-5 shrink-0 place-items-center rounded-full text-[11px] font-bold text-primary-foreground"
          style={{ background: color }}
        >
          {icon}
        </span>
        {label}
      </div>
      <p className="mt-1 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
        {inr(amount)}
      </p>
      {/* 4px rounded data-end, anchored to a baseline that both bars share. */}
      <div className="mt-2 h-3 w-full overflow-hidden rounded-sm bg-muted">
        <div
          className="h-full rounded-r-[4px]"
          style={{ width: `${Math.max(widthPct, 1.5)}%`, background: color }}
        />
      </div>
      <p className={`mt-2 text-xs ${failing ? 'font-medium' : ''} text-muted-foreground tabular`}>
        {failing && (
          <span aria-hidden className="mr-1" style={{ color }}>
            ▲
          </span>
        )}
        {footnote}
      </p>
    </div>
  )
}

function Stat({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-subtle-foreground">{label}</dt>
      <dd className={`tabular ${emphasis ? 'text-lg font-semibold' : 'text-base'} text-foreground`}>
        {value}
      </dd>
    </div>
  )
}
