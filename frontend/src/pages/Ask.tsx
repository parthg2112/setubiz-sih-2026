import { useEffect, useMemo, useState } from 'react'
import { api, type AdvisoryInput, type GroupMemberInput } from '../api'
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

type StepKey = 'who' | 'count' | 'member' | 'village' | 'distance' | 'business' | 'savings' | 'about'

interface Step {
  key: StepKey
  label: string
  title: string
  help: string
  /** Index into the member list, for the repeated member steps. */
  member?: number
}

interface MemberDraft {
  name: string
  social: string
  income: string
  contribution: string
}

const emptyMember = (): MemberDraft => ({ name: '', social: 'sc', income: '', contribution: '' })
const digits = (s: string) => Number(s.replace(/[^\d]/g, ''))

/** The Ask flow asks one thing per screen.
 *
 *  The previous build put nine controls on a single page. For a reader who has not filled in a
 *  web form before, that page is a wall: there is no way to tell what is required, what order to
 *  work in, or whether an answer was accepted. Each screen is one question, in the second person.
 *
 *  Group mode is entered at the first question and inserts its own steps, so someone applying
 *  alone never sees any of it.
 */
export function Ask({ language, strings, onSubmit }: Props) {
  const [step, setStep] = useState(0)
  const [mode, setMode] = useState<'single' | 'group'>('single')
  const [members, setMembers] = useState<MemberDraft[]>([emptyMember(), emptyMember()])
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

  const isGroup = mode === 'group'
  const savingsNumber = digits(savings)
  const pooled = members.reduce((sum, m) => sum + digits(m.contribution), 0)

  const steps = useMemo<Step[]>(() => {
    const who: Step = {
      key: 'who',
      label: strings.whoLabel,
      title: strings.whoTitle,
      help: strings.whoHelp,
    }
    const tail: Step[] = [
      {
        key: 'village',
        label: strings.step1Label,
        title: strings.step1Title,
        help: strings.step1Help,
      },
      {
        key: 'distance',
        label: strings.step2Label,
        title: strings.step2Title,
        help: strings.step2Help,
      },
      {
        key: 'business',
        label: strings.step3Label,
        title: strings.step3Title,
        help: strings.step3Help,
      },
    ]
    if (!isGroup) {
      return [
        who,
        ...tail,
        {
          key: 'savings',
          label: strings.step4Label,
          title: strings.step4Title,
          help: strings.step4Help,
        },
        {
          key: 'about',
          label: strings.step5Label,
          title: strings.step5Title,
          help: strings.step5Help,
        },
      ]
    }
    // Group: how many, then one screen per person, keeping the one-question rhythm. Savings is
    // absent because the group's margin is the sum of what each member puts in.
    return [
      who,
      {
        key: 'count',
        label: strings.countLabel,
        title: strings.countTitle,
        help: strings.countHelp,
      },
      ...members.map((_, i) => ({
        key: 'member' as const,
        label: `${strings.memberLabel} ${i + 1}`,
        title: strings.memberTitle.replace('{n}', String(i + 1)),
        help: strings.memberHelp,
        member: i,
      })),
      ...tail,
      {
        key: 'about',
        label: strings.step5Label,
        title: strings.step5Title,
        help: strings.step5Help,
      },
    ]
  }, [isGroup, members, strings])

  const current = steps[Math.min(step, steps.length - 1)]

  /** Why this step cannot be left, in the reader's language — or null when it can. */
  const blocker = useMemo<string | null>(() => {
    if (current.key === 'village' && !village) return strings.pickVillage
    if (current.key === 'business' && !category) return strings.pickBusiness
    if (current.key === 'savings' && !(savingsNumber > 0)) return strings.savingsTooLow
    if (current.key === 'member') {
      const m = members[current.member ?? 0]
      if (!(digits(m.contribution) > 0)) return strings.contributionTooLow
    }
    return null
  }, [current, village, category, savingsNumber, members, strings])

  function setMember(index: number, patch: Partial<MemberDraft>) {
    setMembers((prev) => prev.map((m, i) => (i === index ? { ...m, ...patch } : m)))
    setShowError(false)
  }

  function setCount(n: number) {
    setMembers((prev) => {
      const next = prev.slice(0, n)
      while (next.length < n) next.push(emptyMember())
      return next
    })
  }

  function advance() {
    if (blocker) {
      setShowError(true)
      return
    }
    setShowError(false)
    if (step < steps.length - 1) {
      setStep(step + 1)
      return
    }
    if (!village) return

    const groupMembers: GroupMemberInput[] = members.map((m) => ({
      name: m.name || null,
      social_category: m.social,
      annual_family_income: m.income ? digits(m.income) : null,
      contribution: digits(m.contribution),
    }))

    const input: AdvisoryInput = {
      village_shrid: village.shrid,
      state: village.state,
      // The backend pools contributions in group mode; `savings` still has to be positive.
      savings: isGroup ? pooled : savingsNumber,
      business_category: category,
      social_category: isGroup ? groupMembers[0].social_category : social,
      annual_family_income: isGroup ? null : income ? digits(income) : null,
      is_woman: isWoman,
      has_prior_experience: experienced,
      radius_km: radius,
      moratorium_mode: 'serviced',
      language,
      ...(isGroup ? { members: groupMembers, liability_split: 'equal' as const } : {}),
    }
    onSubmit(`?${toSearchParams(input).toString()}`)
  }

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
          {current.key === 'who' && (
            <div
              className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s"
              role="radiogroup"
              aria-label={strings.whoTitle}
            >
              <Choice
                name="who"
                checked={!isGroup}
                onChange={() => setMode('single')}
                label={strings.whoSingle}
                description={strings.whoSingleHelp}
              />
              <Choice
                name="who"
                checked={isGroup}
                onChange={() => setMode('group')}
                label={strings.whoGroup}
                description={strings.whoGroupHelp}
              />
            </div>
          )}

          {current.key === 'count' && (
            <div className="ux4g-slider-field ux4g-slider-md">
              <div className="ux4g-slider-label-row">
                <label className="ux4g-slider-label" htmlFor="count">
                  {strings.countLabel}
                </label>
                <span className="ux4g-slider-range-box setubiz-tabular">{members.length}</span>
              </div>
              <div className="ux4g-slider ux4g-slider-md">
                <input
                  type="range"
                  className="ux4g-slider-input"
                  id="count"
                  min={2}
                  max={10}
                  step={1}
                  value={members.length}
                  onChange={(e) => setCount(Number(e.target.value))}
                />
                <div className="ux4g-slider-track">
                  <div
                    className="ux4g-slider-fill"
                    style={{ width: `${((members.length - 2) / 8) * 100}%` }}
                  />
                  <div
                    className="ux4g-slider-thumb"
                    style={{ left: `${((members.length - 2) / 8) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {current.key === 'member' && (
            <MemberForm
              index={current.member ?? 0}
              draft={members[current.member ?? 0]}
              onChange={(patch) => setMember(current.member ?? 0, patch)}
              language={language}
              strings={strings}
            />
          )}

          {current.key === 'village' && (
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

          {current.key === 'distance' && (
            <div className="ux4g-slider-field ux4g-slider-md">
              <div className="ux4g-slider-label-row">
                {/* The card heading already asks the question; repeating it on the control would
                    be the same sentence twice. The label carries the unit instead. */}
                <label className="ux4g-slider-label" htmlFor="radius">
                  {strings.step2Label} ({strings.km})
                </label>
                <span className="ux4g-slider-range-box setubiz-tabular">{radius}</span>
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
                  <div
                    className="ux4g-slider-fill"
                    style={{ width: `${((radius - 3) / 27) * 100}%` }}
                  />
                  <div
                    className="ux4g-slider-thumb"
                    style={{ left: `${((radius - 3) / 27) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {current.key === 'business' && (
            <div
              className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s"
              role="radiogroup"
              aria-label={strings.business}
            >
              {/* Radios rather than chips: each option carries what the unit actually costs, and
                  that number is the single most useful thing at this moment. */}
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

          {current.key === 'savings' && (
            <Money
              id="savings"
              label={strings.savings}
              value={savings}
              helper={savingsNumber > 0 ? inr(savingsNumber) : strings.marginGloss}
              onChange={(v) => {
                setSavings(v)
                setShowError(false)
              }}
            />
          )}

          {current.key === 'about' && (
            <>
              {isGroup ? (
                <p className="ux4g-body-l-default setubiz-measure setubiz-tabular">
                  {strings.groupPooled} {inr(pooled)}
                </p>
              ) : (
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

                  <Money
                    id="income"
                    label={strings.income}
                    value={income}
                    onChange={setIncome}
                  />

                  <Check
                    checked={isWoman}
                    onChange={setIsWoman}
                    label={strings.woman}
                  />
                </>
              )}

              <Check checked={experienced} onChange={setExperienced} label={strings.experienced} />
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
            disabled={step === 0}
            onClick={() => {
              setShowError(false)
              setStep(step - 1)
            }}
          >
            {strings.backStep}
          </button>
          <button type="submit" className="ux4g-btn ux4g-btn-primary ux4g-btn-lg">
            {step === steps.length - 1 ? strings.submit : strings.next}
          </button>
        </div>
      </form>
    </div>
  )
}

function MemberForm({
  index,
  draft,
  onChange,
  language,
  strings,
}: {
  index: number
  draft: MemberDraft
  onChange: (patch: Partial<MemberDraft>) => void
  language: Language
  strings: Strings
}) {
  return (
    <>
      <div className="ux4g-input-container ux4g-input-lg">
        <label className="ux4g-label-l-strong" htmlFor={`m${index}-name`}>
          {strings.memberName}
        </label>
        <div className="ux4g-input">
          <input
            id={`m${index}-name`}
            className="ux4g-input-input"
            type="text"
            autoComplete="off"
            value={draft.name}
            onChange={(e) => onChange({ name: e.target.value })}
          />
        </div>
      </div>

      <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
        <label className="ux4g-label-l-strong" htmlFor={`m${index}-social`}>
          {strings.social}
        </label>
        <select
          id={`m${index}-social`}
          className="ux4g-form-select ux4g-form-select-lg"
          value={draft.social}
          onChange={(e) => onChange({ social: e.target.value })}
        >
          {SOCIAL_CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {language === 'hi' ? c.hi : c.en}
            </option>
          ))}
        </select>
      </div>

      <Money
        id={`m${index}-income`}
        label={strings.income}
        value={draft.income}
        onChange={(v) => onChange({ income: v })}
      />
      <Money
        id={`m${index}-contribution`}
        label={strings.memberContribution}
        value={draft.contribution}
        helper={digits(draft.contribution) > 0 ? inr(digits(draft.contribution)) : undefined}
        onChange={(v) => onChange({ contribution: v })}
      />
    </>
  )
}

function Money({
  id,
  label,
  value,
  helper,
  onChange,
}: {
  id: string
  label: string
  value: string
  helper?: string
  onChange: (v: string) => void
}) {
  return (
    <div className="ux4g-input-container ux4g-input-lg">
      <label className="ux4g-label-l-strong" htmlFor={id}>
        {label}
      </label>
      <div className="ux4g-input">
        <span className="ux4g-icon-outlined ux4g-input-leading-icon" aria-hidden="true">
          currency_rupee
        </span>
        <input
          id={id}
          className="ux4g-input-input setubiz-tabular"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={value}
          aria-describedby={helper ? `${id}-helper` : undefined}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
      {/* Echoes the amount back in grouped Indian digits, so a mistyped extra zero is visible
          before it becomes a wrong loan. */}
      {helper && (
        <div className="ux4g-input-helper" id={`${id}-helper`}>
          <span className="ux4g-input-helper-text setubiz-tabular">{helper}</span>
        </div>
      )}
    </div>
  )
}

function Choice({
  name,
  checked,
  onChange,
  label,
  description,
}: {
  name: string
  checked: boolean
  onChange: () => void
  label: string
  description: string
}) {
  return (
    <label className="ux4g-radio ux4g-radio-md">
      <input className="ux4g-radio-input" type="radio" name={name} checked={checked} onChange={onChange} />
      <div className="ux4g-radio-control">
        <span className="ux4g-radiomark" />
      </div>
      <div className="ux4g-radio-content">
        <div className="ux4g-radio-header">
          <span className="ux4g-radio-label">{label}</span>
        </div>
        <div className="ux4g-radio-description">{description}</div>
      </div>
    </label>
  )
}

function Check({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
}) {
  return (
    <label className="ux4g-checkbox ux4g-checkbox-md">
      <input
        className="ux4g-checkbox-input"
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <div className="ux4g-checkbox-control">
        <span className="ux4g-checkmark" />
      </div>
      <div className="ux4g-checkbox-content">
        <div className="ux4g-checkbox-header">
          <span className="ux4g-checkbox-label">{label}</span>
        </div>
      </div>
    </label>
  )
}

function Stepper({
  steps,
  current,
  strings,
}: {
  steps: Step[]
  current: number
  strings: Strings
}) {
  const position = strings.stepOf
    .replace('{n}', String(current + 1))
    .replace('{total}', String(steps.length))

  return (
    <nav aria-label={position}>
      {/* Announced to assistive technology and shown on small screens, where the full stepper is
          too wide to read. */}
      <p className="ux4g-label-l-strong ux4g-mb-s">{position}</p>
      <ol className="ux4g-stepper ux4g-stepper-horizontal ux4g-d-none ux4g-md-d-flex">
        {steps.map((s, i) => {
          const state =
            i < current
              ? 'ux4g-stepper-completed'
              : i === current
                ? 'ux4g-stepper-inprogress'
                : 'ux4g-stepper-step-pending'
          return (
            <li className={`ux4g-stepper-step ${state}`} key={`${s.key}-${s.member ?? i}`}>
              <span
                className={`ux4g-stepper-head ${
                  i === current ? 'ux4g-stepper-head-icon-active' : ''
                }`}
                aria-hidden="true"
              >
                {i < current ? <span className="ux4g-icon-outlined">check</span> : <span>{i + 1}</span>}
              </span>
              <span
                className="ux4g-stepper-label"
                aria-current={i === current ? 'step' : undefined}
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
