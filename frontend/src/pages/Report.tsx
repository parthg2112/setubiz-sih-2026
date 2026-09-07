import { useState } from 'react'
import { BandBar } from '../components/BandBar'
import { DscrChart } from '../components/DscrChart'
import { LoanComparison } from '../components/LoanComparison'
import { ProvenancePanel } from '../components/ProvenancePanel'
import { ScheduleTable } from '../components/ScheduleTable'
import { SeasonalityChart } from '../components/SeasonalityChart'
import { SwotGrid } from '../components/SwotGrid'
import { inr, lakh, type Strings } from '../format'
import type { AdvisoryResponse, DscrYear, Language, ReportSection } from '../types'

interface Props {
  data: AdvisoryResponse
  language: Language
  strings: Strings
  onRestart: () => void
}

export function Report({ data, language, strings, onRestart }: Props) {
  const [provenanceOpen, setProvenanceOpen] = useState(false)
  const { facts, report, validation } = data
  const section = (id: string) => report.sections.find((s) => s.id === id)

  const loan = section('loan_structure')
  const stress = section('stress')
  const competition = section('competition')
  const marketReach = section('market_reach')
  const swot = section('swot')
  const threats = section('threats')

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-6">
      <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            {language === 'hi' && facts.village.name_hi ? facts.village.name_hi : facts.village.name}
            <span className="ml-2 text-base font-normal text-ink-2">
              {facts.village.block} · {facts.village.district}
            </span>
          </h1>
          <p className="mt-0.5 text-sm text-ink-2">
            {language === 'hi' && facts.template.name_hi
              ? facts.template.name_hi
              : facts.template.name}{' '}
            · {facts.scheme.scheme_name}
          </p>
        </div>
        <div className="no-print flex gap-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-lg border border-hairline px-3 py-2 text-sm text-ink-2 hover:text-ink"
          >
            {strings.print}
          </button>
          <button
            type="button"
            onClick={onRestart}
            className="rounded-lg border border-hairline px-3 py-2 text-sm text-ink-2 hover:text-ink"
          >
            {strings.back}
          </button>
        </div>
      </header>

      {facts.contains_synthetic_data && (
        <p
          className="mb-5 rounded-lg px-4 py-3 text-sm"
          style={{
            background: 'color-mix(in srgb, var(--status-warning) 20%, transparent)',
            color: 'var(--text-primary)',
          }}
        >
          <strong className="font-semibold">⚠ {strings.synthetic}.</strong> {strings.syntheticNote}
        </p>
      )}

      {loan?.data.max_loan && (
        <LoanComparison
          maxLoan={loan.data.max_loan}
          recommendedLoan={loan.data.recommended_loan ?? '0'}
          headroom={loan.data.headroom ?? '0'}
          requiredCapital={loan.data.required_capital ?? '0'}
          debtNeed={loan.data.debt_need ?? '0'}
          binding={loan.data.binding ?? ''}
          maxMinDscr={facts.right_sizing.max_loan_min_dscr}
          recommendedMinDscr={facts.right_sizing.recommended_min_dscr}
          dscrThreshold={facts.right_sizing.dscr_threshold}
          language={language}
          strings={strings}
        />
      )}

      <button
        type="button"
        onClick={() => setProvenanceOpen(true)}
        className="no-print mt-3 w-full rounded-lg border border-dashed border-hairline px-4 py-2.5 text-sm font-medium text-accent"
      >
        {strings.provenance} ({Object.keys(facts.numeric_index).length})
      </button>

      {facts.warnings.length > 0 && (
        <ul className="print-block mt-5 space-y-2">
          {facts.warnings.map((warning) => (
            <li
              key={warning.id}
              className="flex gap-2 rounded-lg px-4 py-3 text-sm leading-relaxed"
              style={{ background: 'color-mix(in srgb, var(--status-serious) 14%, transparent)' }}
            >
              <span aria-hidden style={{ color: 'var(--status-critical)' }}>
                ▲
              </span>
              <span className="text-ink-2">
                {language === 'hi' ? warning.text_hi : warning.text_en}
              </span>
            </li>
          ))}
        </ul>
      )}

      <Prose section={section('headline')} />
      <Prose section={loan} />

      {stress?.data.recommended && (
        <Block title={stress.heading} cites={stress.cites} facts={data}>
          <p className="mb-3 text-sm leading-relaxed text-ink-2">{stress.body}</p>
          <DscrChart
            base={(stress.data.recommended as DscrYear[]) ?? []}
            scenarios={stress.data.scenarios ?? []}
            threshold={stress.data.dscr_threshold ?? facts.right_sizing.dscr_threshold}
            stressFloor={stress.data.stress_floor ?? facts.right_sizing.stress_floor}
            language={language}
          />
        </Block>
      )}

      {facts.amortization_recommended && (
        <Block title={section('repayment')?.heading ?? ''} cites={section('repayment')?.cites ?? []} facts={data}>
          <p className="mb-4 text-sm leading-relaxed text-ink-2">{section('repayment')?.body}</p>
          <ScheduleTable
            rows={facts.amortization_recommended.schedule}
            mode={section('repayment')?.data.mode ?? 'serviced'}
            alternateMode={facts.amortization_alternate_mode?.mode ?? null}
            alternateInstalment={facts.amortization_alternate_mode?.instalment ?? null}
            language={language}
            strings={strings}
          />
        </Block>
      )}

      {marketReach && (
        <Block title={marketReach.heading} cites={marketReach.cites} facts={data}>
          <p className="text-sm leading-relaxed text-ink-2">{marketReach.body}</p>
          {marketReach.data.villages && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {marketReach.data.villages.map((v) => (
                <li
                  key={v.name}
                  className="tabular rounded-full border border-hairline px-2.5 py-1 text-xs text-ink-2"
                >
                  {language === 'hi' && v.name_hi ? v.name_hi : v.name} · {v.distance_km} km
                </li>
              ))}
            </ul>
          )}
        </Block>
      )}

      {competition?.data.band && (
        <Block title={competition.heading} cites={competition.cites} facts={data}>
          <p className="mb-3 text-sm leading-relaxed text-ink-2">{competition.body}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <BandBar
              band={competition.data.band}
              format={(v) => String(Math.round(Number(v)))}
              label={language === 'en' ? 'Existing enterprises' : 'मौजूदा इकाइयाँ'}
              language={language}
            />
            {threats?.data.price_band && (
              <BandBar
                band={threats.data.price_band}
                format={(v) => inr(v)}
                label={language === 'en' ? 'Market price spread' : 'बाज़ार मूल्य सीमा'}
                language={language}
              />
            )}
          </div>
        </Block>
      )}

      {swot?.data.quadrants && (
        <Block title={swot.heading} cites={swot.cites} facts={data}>
          <SwotGrid quadrants={swot.data.quadrants} labels={strings.quadrant} />
        </Block>
      )}

      {threats && (
        <Block title={threats.heading} cites={threats.cites} facts={data}>
          <ul className="space-y-2">
            {(threats.data.items ?? []).map((item) => (
              <li key={item.id} className="flex gap-2 text-sm leading-relaxed text-ink-2">
                <span
                  aria-hidden
                  className="mt-0.5 shrink-0 text-xs"
                  style={{
                    color:
                      item.severity === 'high'
                        ? 'var(--status-critical)'
                        : 'var(--status-serious)',
                  }}
                >
                  ▲
                </span>
                <span>
                  {item.text}{' '}
                  <span className="text-xs uppercase tracking-wide text-ink-muted">
                    {item.severity}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          {threats.data.seasonality?.months && (
            <div className="mt-4">
              <SeasonalityChart
                months={threats.data.seasonality.months}
                arrivals={threats.data.seasonality.arrivals ?? []}
                commodity={threats.data.seasonality.commodity ?? ''}
                market={threats.data.seasonality.market ?? ''}
                peakMonth={threats.data.seasonality.peak_month}
                troughMonth={threats.data.seasonality.trough_month}
                language={language}
              />
            </div>
          )}
        </Block>
      )}

      <Block title={section('scheme')?.heading ?? ''} cites={section('scheme')?.cites ?? []} facts={data}>
        <p className="text-sm leading-relaxed text-ink-2">{section('scheme')?.body}</p>
        <h4 className="mt-4 text-sm font-semibold text-ink">{strings.documents}</h4>
        <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
          {facts.eligibility.documents.map((doc) => (
            <li key={doc.en} className="flex gap-2 text-sm text-ink-2">
              <span aria-hidden className="text-ink-muted">
                ☐
              </span>
              {language === 'hi' && doc.hi ? doc.hi : doc.en}
            </li>
          ))}
        </ul>
      </Block>

      <footer className="mt-8 border-t border-hairline pt-4 text-xs text-ink-muted">
        <p>
          {section('data_note')?.body}
        </p>
        <p className="mt-2 tabular">
          {validation.checked} {strings.grounded} ·{' '}
          {validation.passed ? '✓' : '✗'} · narrator: {report.narrator} ·{' '}
          {lakh(facts.numeric_index.addressable_market_point ?? '0')}{' '}
          {language === 'en' ? 'addressable market' : 'कुल बाज़ार'}
        </p>
      </footer>

      <ProvenancePanel
        facts={facts}
        open={provenanceOpen}
        onClose={() => setProvenanceOpen(false)}
        language={language}
        closeLabel={strings.close}
      />
    </div>
  )
}

function Prose({ section }: { section?: ReportSection }) {
  if (!section) return null
  return (
    <section className="print-block mt-6">
      <h2 className="text-lg font-semibold text-ink">{section.heading}</h2>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-2">{section.body}</p>
    </section>
  )
}

function Block({
  title,
  cites,
  facts,
  children,
}: {
  title: string
  cites: string[]
  facts: AdvisoryResponse
  children: React.ReactNode
}) {
  const titles = cites
    .map((id) => facts.facts.sources.find((s) => s.id === id)?.title)
    .filter(Boolean)
  return (
    <section className="print-block mt-8">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <div className="mt-2">{children}</div>
      {titles.length > 0 && (
        <p className="mt-2 text-[11px] leading-snug text-ink-muted">Source: {titles.join(' · ')}</p>
      )}
    </section>
  )
}
