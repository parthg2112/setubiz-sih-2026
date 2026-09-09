import { useEffect, useState } from 'react'
import { api, type AdvisoryInput } from '../api'
import { inr, type Strings } from '../format'
import { VillagePicker } from '../components/VillagePicker'
import type { CostTemplate, Language, VillageMatch } from '../types'

interface Props {
  language: Language
  strings: Strings
  onSubmit: (input: AdvisoryInput) => void
  busy: boolean
  error: string | null
}

const SOCIAL_CATEGORIES = [
  { value: 'sc', en: 'Scheduled Caste', hi: 'अनुसूचित जाति' },
  { value: 'safai_karamchari', en: 'Safai karamchari', hi: 'सफाई कर्मचारी' },
  { value: 'obc', en: 'OBC', hi: 'अन्य पिछड़ा वर्ग' },
  { value: 'ebc', en: 'EBC', hi: 'अत्यंत पिछड़ा वर्ग' },
  { value: 'general', en: 'General', hi: 'सामान्य' },
]

export function Ask({ language, strings, onSubmit, busy, error }: Props) {
  const [village, setVillage] = useState<VillageMatch | null>(null)
  const [savings, setSavings] = useState('100000')
  const [category, setCategory] = useState('dairy')
  const [social, setSocial] = useState('sc')
  const [income, setIncome] = useState('280000')
  const [isWoman, setIsWoman] = useState(false)
  const [experienced, setExperienced] = useState(true)
  const [radius, setRadius] = useState(10)
  const [templates, setTemplates] = useState<CostTemplate[]>([])

  useEffect(() => {
    api.costTemplates().then(setTemplates).catch(() => setTemplates([]))
  }, [])

  const savingsNumber = Number(savings.replace(/[^\d]/g, ''))
  const ready = village !== null && savingsNumber > 0 && !busy

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!village || savingsNumber <= 0) return
    onSubmit({
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
    })
  }

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-2xl space-y-5 px-4 py-8">
      <VillagePicker
        value={village}
        onChange={setVillage}
        state="Jharkhand"
        language={language}
        strings={strings}
      />

      <div>
        <label htmlFor="savings" className="block text-sm font-medium text-muted-foreground">
          {strings.savings}
        </label>
        <input
          id="savings"
          inputMode="numeric"
          value={savings}
          onChange={(e) => setSavings(e.target.value)}
          className="tabular mt-1.5 w-full rounded-lg border border-border bg-card px-4 py-3 text-base text-foreground outline-none focus:border-primary"
        />
        <p className="mt-1 text-xs text-subtle-foreground">{inr(savingsNumber)}</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-muted-foreground">{strings.business}</label>
        <div className="mt-1.5 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {templates.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setCategory(t.category)}
              aria-pressed={category === t.category}
              className="rounded-lg border px-3 py-3 text-left text-sm transition-colors"
              style={{
                borderColor: category === t.category ? 'var(--primary)' : 'var(--border)',
                background:
                  category === t.category
                    ? 'color-mix(in srgb, var(--primary) 8%, var(--card))'
                    : 'var(--card)',
              }}
            >
              <span className="block font-medium text-foreground">
                {language === 'hi' && t.name_hi ? t.name_hi : t.name}
              </span>
              <span className="tabular block text-xs text-subtle-foreground">
                {inr(t.required_capital)}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="social" className="block text-sm font-medium text-muted-foreground">
            {strings.social}
          </label>
          <select
            id="social"
            value={social}
            onChange={(e) => setSocial(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-border bg-card px-4 py-3 text-base text-foreground outline-none focus:border-primary"
          >
            {SOCIAL_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {language === 'hi' ? c.hi : c.en}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="income" className="block text-sm font-medium text-muted-foreground">
            {strings.income}
          </label>
          <input
            id="income"
            inputMode="numeric"
            value={income}
            onChange={(e) => setIncome(e.target.value)}
            className="tabular mt-1.5 w-full rounded-lg border border-border bg-card px-4 py-3 text-base text-foreground outline-none focus:border-primary"
          />
        </div>
      </div>

      <div>
        <label htmlFor="radius" className="block text-sm font-medium text-muted-foreground">
          {strings.radius} <span className="tabular text-subtle-foreground">{radius} km</span>
        </label>
        <input
          id="radius"
          type="range"
          min={3}
          max={30}
          step={1}
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
          className="mt-2 w-full accent-[var(--primary)]"
        />
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2">
        <Checkbox checked={isWoman} onChange={setIsWoman} label={strings.woman} />
        <Checkbox checked={experienced} onChange={setExperienced} label={strings.experienced} />
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg px-4 py-3 text-sm"
          style={{
            background: 'color-mix(in srgb, var(--destructive) 12%, transparent)',
            color: 'var(--foreground)',
          }}
        >
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!ready}
        className="w-full rounded-lg px-4 py-4 text-base font-semibold text-primary-foreground transition-opacity disabled:opacity-40"
        style={{ background: 'var(--primary)' }}
      >
        {busy ? strings.working : strings.submit}
      </button>
    </form>
  )
}

function Checkbox({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-4 accent-[var(--primary)]"
      />
      {label}
    </label>
  )
}
