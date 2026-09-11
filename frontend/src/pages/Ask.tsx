import { useEffect, useMemo, useState } from 'react'
import { api, type AdvisoryInput } from '../api'
import { VillagePicker } from '../components/VillagePicker'
import { inr, type Strings } from '../format'
import type { CostTemplate, Language, VillageMatch } from '../types'
import { toSearchParams } from '../urlState'

interface Props {
  language: Language
  strings: Strings
  onSubmit: (search: string) => void
}

const SOCIAL_CATEGORIES = [
  { value: 'sc', en: 'Scheduled Caste', hi: 'अनुसूचित जाति' },
  { value: 'safai_karamchari', en: 'Safai karamchari', hi: 'सफाई कर्मचारी' },
  { value: 'obc', en: 'Other Backward Class', hi: 'अन्य पिछड़ा वर्ग' },
  { value: 'ebc', en: 'Economically Backward Class', hi: 'अत्यंत पिछड़ा वर्ग' },
  { value: 'general', en: 'General', hi: 'सामान्य' },
]

const TOTAL_STEPS = 5

/** The Ask flow asks one thing per screen.
 *
 *  The previous build put nine controls on a single page. For a reader who has not filled in a
 *  web form before, that page is a wall: there is no way to tell what is required, what order to
 *  work in, or whether an answer was accepted. Splitting it costs four extra taps and removes the
 *  wall — each screen is one question, in the second person, with one thing to decide. */
export function Ask({ language, strings, onSubmit }: Props) {
  const [step, setStep] = useState(1)
  const [village, setVillage] = useState<VillageMatch | null>(null)
  const [radius, setRadius] = useState(10)
  const [category, setCategory] = useState('')
  const [savings, setSavings] = useState('')
  const [social, setSocial] = useState('sc')
  const [income, setIncome] = useState('')
  const [isWoman, setIsWoman] = useState(false)
  const [experienced, setExperienced] = useState(true)
  const [templates, setTemplates] = useState<CostTemplate[]>([])
  const [showError, setShowError] = useState(false)

  useEffect(() => {
    api
      .costTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]))
  }, [])

  const savingsNumber = Number(savings.replace(/[^\d]/g, ''))

  /** Why this step cannot be left, in the reader's language — or null when it can. */
  const blocker = useMemo<string | null>(() => {
    if (step === 1 && !village) return strings.pickVillage
    if (step === 3 && !category) return strings.pickBusiness
    if (step === 4 && !(savingsNumber > 0)) return strings.savingsTooLow
    return null
  }, [step, village, category, savingsNumber, strings])

  const steps = [
    { label: strings.step1Label, title: strings.step1Title, help: strings.step1Help },
    { label: strings.step2Label, title: strings.step2Title, help: strings.step2Help },
    { label: strings.step3Label, title: strings.step3Title, help: strings.step3Help },
    { label: strings.step4Label, title: strings.step4Title, help: strings.step4Help },
    { label: strings.step5Label, title: strings.step5Title, help: strings.step5Help },
  ]

  function advance() {
    if (blocker) {
      setShowError(true)
      return
    }
    setShowError(false)
    if (step < TOTAL_STEPS) {
      setStep(step + 1)
      return
    }
    if (!village) return
    const input: AdvisoryInput = {
      village_shrid: village.shrid,
      state: village.state,
      savings: savingsNumber,
      business_category: category,
      social_category: social,
      annual_family_income: income ? Number(income.replace(/[^\d]/g, '')) : null,
      is_woman: isWoman,
      has_prior_experience: experienced,
      radius_km: radius,
      moratorium_mode: 'serviced',
      language,
    }
    onSubmit(`?${toSearchParams(input).toString()}`)
  }

  const current = steps[step - 1]

  return (
    <div className="ux4g-container ux4g-py-xl">
      <Stepper steps={steps} current={step} strings={strings} />

      <form
        className="ux4g-card ux4g-card-outline ux4g-card-vertical ux4g-mt-l"
        onSubmit={(e) => {
          e.preventDefault()
          advance()
        }}
      >
        <div className="ux4g-card-header">
          {/* The question is the heading. Nothing between the reader and the thing being asked. */}
          <h1 className="ux4g-heading-l-strong ux4g-card-title">{current.title}</h1>
          <p className="ux4g-body-l-default ux4g-card-sub-title setubiz-measure">{current.help}</p>
        </div>

        <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-l">
          {step === 1 && (
            <VillagePicker
              value={village}
              onChange={(v) => {
                setVillage(v)
                setShowError(false)
              }}
              state="Jharkhand"
              language={language}
              strings={strings}
            />
          )}

          {step === 2 && (
            <div className="ux4g-slider-field ux4g-slider-md">
              <div className="ux4g-slider-label-row">
                <label className="ux4g-slider-label" htmlFor="radius">
                  {strings.radius}
                </label>
                <span className="ux4g-slider-range-box setubiz-tabular">
                  {radius} {strings.km}
                </span>
              </div>
              <div className="ux4g-slider ux4g-slider-md">
                <input
                  type="range"
                  className="ux4g-slider-input"
                  id="radius"
                  min={3}
                  max={30}
                  step={1}
                  value={radius}
                  onChange={(e) => setRadius(Number(e.target.value))}
                />
                <div className="ux4g-slider-track">
                  <div className="ux4g-slider-fill" style={{ width: `${((radius - 3) / 27) * 100}%` }} />
                  <div
                    className="ux4g-slider-thumb"
                    style={{ left: `${((radius - 3) / 27) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div
              className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s"
              role="radiogroup"
              aria-label={strings.business}
            >
              {/* Radios rather than chips: each option carries what the unit actually costs, and
                  that number is the single most useful thing at this moment. A chip cannot hold
                  it, and the choice is too consequential to make from a five-word label. */}
              {templates.map((t) => (
                <label className="ux4g-radio ux4g-radio-md" key={t.id}>
                  <input
                    className="ux4g-radio-input"
                    type="radio"
                    name="business"
                    value={t.category}
                    checked={category === t.category}
                    onChange={() => {
                      setCategory(t.category)
                      setShowError(false)
                    }}
                  />
                  <div className="ux4g-radio-control">
                    <span className="ux4g-radiomark" />
                  </div>
                  <div className="ux4g-radio-content">
                    <div className="ux4g-radio-header">
                      <span className="ux4g-radio-label">
                        {language === 'hi' && t.name_hi ? t.name_hi : t.name}
                      </span>
                    </div>
                    <div className="ux4g-radio-description setubiz-tabular">
                      {strings.unitCost} {inr(t.required_capital)}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          )}

          {step === 4 && (
            <div className="ux4g-input-container ux4g-input-lg">
              <label className="ux4g-label-l-strong" htmlFor="savings">
                {strings.savings}
              </label>
              <div className="ux4g-input">
                <span className="ux4g-icon-outlined ux4g-input-leading-icon" aria-hidden="true">
                  currency_rupee
                </span>
                <input
                  id="savings"
                  className="ux4g-input-input setubiz-tabular"
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  value={savings}
                  aria-describedby="savings-helper"
                  onChange={(e) => {
                    setSavings(e.target.value)
                    setShowError(false)
                  }}
                />
              </div>
              {/* Echoes the amount back in grouped Indian digits as it is typed, so a mistyped
                  extra zero is visible before it becomes a wrong loan. */}
              <div className="ux4g-input-helper" id="savings-helper">
                <span className="ux4g-input-helper-text setubiz-tabular">
                  {savingsNumber > 0 ? inr(savingsNumber) : strings.marginGloss}
                </span>
              </div>
            </div>
          )}

          {step === 5 && (
            <>
              <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
                <label className="ux4g-label-l-strong" htmlFor="social">
                  {strings.social}
                </label>
                <select
                  id="social"
                  className="ux4g-form-select ux4g-form-select-lg"
                  value={social}
                  onChange={(e) => setSocial(e.target.value)}
                >
                  {SOCIAL_CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>
                      {language === 'hi' ? c.hi : c.en}
                    </option>
                  ))}
                </select>
              </div>

              <div className="ux4g-input ux4g-input-lg">
                <label className="ux4g-label-l-strong" htmlFor="income">
                  {strings.income}
                </label>
                <div className="ux4g-input-container">
                  <span className="ux4g-icon-outlined ux4g-input-leading-icon" aria-hidden="true">
                    currency_rupee
                  </span>
                  <input
                    id="income"
                    className="ux4g-input-input setubiz-tabular"
                    inputMode="numeric"
                    autoComplete="off"
                    value={income}
                    onChange={(e) => setIncome(e.target.value)}
                  />
                </div>
              </div>

              <label className="ux4g-checkbox ux4g-checkbox-md">
                <input
                  className="ux4g-checkbox-input"
                  type="checkbox"
                  checked={isWoman}
                  onChange={(e) => setIsWoman(e.target.checked)}
                />
                <div className="ux4g-checkbox-control">
                  <span className="ux4g-checkmark" />
                </div>
                <div className="ux4g-checkbox-content">
                  <div className="ux4g-checkbox-header">
                    <span className="ux4g-checkbox-label">{strings.woman}</span>
                  </div>
                </div>
              </label>

              <label className="ux4g-checkbox ux4g-checkbox-md">
                <input
                  className="ux4g-checkbox-input"
                  type="checkbox"
                  checked={experienced}
                  onChange={(e) => setExperienced(e.target.checked)}
                />
                <div className="ux4g-checkbox-control">
                  <span className="ux4g-checkmark" />
                </div>
                <div className="ux4g-checkbox-content">
                  <div className="ux4g-checkbox-header">
                    <span className="ux4g-checkbox-label">{strings.experienced}</span>
                  </div>
                </div>
              </label>
            </>
          )}

          {showError && blocker && (
            <div className="ux4g-alert ux4g-alert-error" role="alert">
              <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
                error
              </span>
              <div className="ux4g-alert-content">
                <p className="ux4g-alert-message">{blocker}</p>
              </div>
            </div>
          )}
        </div>

        <div className="ux4g-card-footer ux4g-d-flex ux4g-jc-between ux4g-ai-center ux4g-gap-x-m">
          <button
            type="button"
            className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
            disabled={step === 1}
            onClick={() => {
              setShowError(false)
              setStep(step - 1)
            }}
          >
            {strings.backStep}
          </button>
          <button type="submit" className="ux4g-btn ux4g-btn-primary ux4g-btn-lg">
            {step === TOTAL_STEPS ? strings.submit : strings.next}
          </button>
        </div>
      </form>
    </div>
  )
}

function Stepper({
  steps,
  current,
  strings,
}: {
  steps: { label: string }[]
  current: number
  strings: Strings
}) {
  const position = strings.stepOf
    .replace('{n}', String(current))
    .replace('{total}', String(steps.length))

  return (
    <nav aria-label={position}>
      {/* Announced to assistive technology and shown on small screens, where the full stepper is
          too wide to read. */}
      <p className="ux4g-label-l-strong ux4g-mb-s">{position}</p>
      <ol className="ux4g-stepper ux4g-stepper-horizontal ux4g-d-none ux4g-md-d-flex">
        {steps.map((s, i) => {
          const index = i + 1
          const state =
            index < current
              ? 'ux4g-stepper-completed'
              : index === current
                ? 'ux4g-stepper-inprogress'
                : 'ux4g-stepper-step-pending'
          return (
            <li className={`ux4g-stepper-step ${state}`} key={s.label}>
              <span
                className={`ux4g-stepper-head ${
                  index === current ? 'ux4g-stepper-head-icon-active' : ''
                }`}
                aria-hidden="true"
              >
                {index < current ? (
                  <span className="ux4g-icon-outlined">check</span>
                ) : (
                  <span>{index}</span>
                )}
              </span>
              <span
                className="ux4g-stepper-label"
                aria-current={index === current ? 'step' : undefined}
              >
                {s.label}
              </span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
