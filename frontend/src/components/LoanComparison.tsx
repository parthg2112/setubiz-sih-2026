import type { CSSProperties } from 'react'
import { BINDING_LABEL, inr, ratio, type Strings } from '../format'
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
  strings: Strings
}

/** The answer, and the product's whole argument in one card.
 *
 *  The recommended figure leads at display size and is stated as a sentence, because that is the
 *  one thing a reader must leave with. The scheme's permitted maximum sits underneath as the
 *  contrast — deliberately second, since presenting it first is exactly the framing that causes
 *  the over-borrowing this service exists to prevent.
 *
 *  Status colour never carries meaning alone: each figure has an icon and a written label. */
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
  const maxFails = Number(maxMinDscr) < Number(dscrThreshold)

  return (
    <div className="ux4g-card ux4g-card-outline ux4g-card-vertical">
      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-l">
        <div>
          <p className="ux4g-label-l-default ux4g-text-neutral-secondary">{strings.answerLead}</p>
          <p className="ux4g-display-s-strong ux4g-text-primary setubiz-tabular">
            {inr(recommendedLoan)}
          </p>
          <p className="ux4g-body-l-default setubiz-measure">
            {strings.answerBecause} {bindingLabel}.
          </p>
        </div>

        <div className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-2 ux4g-gap-l">
          <Figure
            tone="success"
            icon="check_circle"
            label={strings.recommended}
            amount={recommendedLoan}
            pct={(recommended / scale) * 100}
            footnote={`${strings.worstYear} ${ratio(recommendedMinDscr)} · ${bindingLabel}`}
            failing={false}
          />
          <Figure
            tone="error"
            icon="warning"
            label={strings.maxLoan}
            amount={maxLoan}
            pct={(max / scale) * 100}
            footnote={`${strings.worstYear} ${ratio(maxMinDscr)} · ${
              language === 'en' ? 'norm' : 'मानक'
            } ${ratio(dscrThreshold)}`}
            failing={maxFails}
          />
        </div>

        <div className="ux4g-divider-horizontal" />

        <dl className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-3 ux4g-gap-m">
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
      </div>
    </div>
  )
}

function Figure({
  tone,
  icon,
  label,
  amount,
  pct,
  footnote,
  failing,
}: {
  tone: 'success' | 'error'
  icon: string
  label: string
  amount: string
  pct: number
  footnote: string
  failing: boolean
}) {
  // The component reads its own --ux4g-progress-value token; this is how it is parameterised,
  // not a hardcoded style.
  const fill = { '--ux4g-progress-value': Math.max(pct, 1.5) } as CSSProperties

  return (
    <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
      <p className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs ux4g-label-l-strong">
        <span className={`ux4g-icon-outlined ux4g-text-${tone}`} aria-hidden="true">
          {icon}
        </span>
        {label}
      </p>
      <p className="ux4g-heading-xl-strong setubiz-tabular">{inr(amount)}</p>
      <div className="ux4g-progress-bar">
        <div className="ux4g-progress-bar-track">
          <div className="ux4g-progress-bar-fill" style={fill} />
        </div>
      </div>
      <p
        className={`ux4g-body-s-default setubiz-tabular ${
          failing ? 'ux4g-text-error' : 'ux4g-text-neutral-secondary'
        }`}
      >
        {footnote}
      </p>
    </div>
  )
}

function Stat({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div>
      <dt className="ux4g-body-s-default ux4g-text-neutral-tertiary">{label}</dt>
      <dd
        className={`setubiz-tabular ${
          emphasis ? 'ux4g-title-m-strong' : 'ux4g-body-l-default'
        }`}
      >
        {value}
      </dd>
    </div>
  )
}
