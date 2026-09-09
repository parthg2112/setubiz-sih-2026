import { useState, type ReactNode } from 'react'
import { BandBar } from '../components/BandBar'
import { DscrChart } from '../components/DscrChart'
import { LoanComparison } from '../components/LoanComparison'
import { ProvenancePanel } from '../components/ProvenancePanel'
import { ReportNav, type NavItem } from '../components/ReportNav'
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

/** One section of the report: the nav and the page are built from the same list, so a section
 *  the pipeline did not emit can never leave a dead link in the contents. */
interface Entry {
  id: string
  label: string
  node: ReactNode
}

export function Report({ data, language, strings, onRestart }: Props) {
  const [provenanceOpen, setProvenanceOpen] = useState(false)
  const { facts, report, validation } = data
  const section = (id: string) => report.sections.find((s) => s.id === id)

  const headline = section('headline')
  const loan = section('loan_structure')
  const stress = section('stress')
  const repayment = section('repayment')
  const marketReach = section('market_reach')
  const competition = section('competition')
  const swot = section('swot')
  const threats = section('threats')
  const scheme = section('scheme')

  const sourceTitles = (cites: string[]) =>
    cites.map((id) => facts.sources.find((s) => s.id === id)?.title).filter(Boolean) as string[]

  const entries: (Entry | false | null | undefined)[] = [
    {
      id: 'answer',
      label: strings.keyFigures,
      node: (
        <div className="space-y-4">
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
          {facts.warnings.length > 0 && (
            <section
              className="print-block rounded-lg border p-5 sm:p-6"
              style={{
                borderColor: 'color-mix(in srgb, var(--destructive) 35%, transparent)',
                background: 'color-mix(in srgb, var(--destructive) 8%, var(--card))',
              }}
            >
              <h2 className="text-sm font-semibold tracking-tight text-foreground">
                <span aria-hidden style={{ color: 'var(--destructive)' }}>
                  ▲
                </span>{' '}
                {strings.warningsHeading}
              </h2>
              <ul className="mt-3 space-y-2.5">
                {facts.warnings.map((warning) => (
                  <li
                    key={warning.id}
                    className="text-[15px] leading-7 text-muted-foreground max-w-[68ch]"
                  >
                    {language === 'hi' ? warning.text_hi : warning.text_en}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      ),
    },
    headline && {
      id: 'headline',
      label: headline.heading,
      node: <Card heading={headline.heading} cites={sourceTitles(headline.cites)} strings={strings}>
        <Body>{headline.body}</Body>
      </Card>,
    },
    loan && {
      id: 'loan_structure',
      label: loan.heading,
      node: (
        <Card heading={loan.heading} cites={sourceTitles(loan.cites)} strings={strings}>
          <Body>{loan.body}</Body>
        </Card>
      ),
    },
    stress?.data.recommended && {
      id: 'stress',
      label: stress.heading,
      node: (
        <Card heading={stress.heading} cites={sourceTitles(stress.cites)} strings={strings}>
          <Body>{stress.body}</Body>
          <div className="mt-5">
            <DscrChart
              base={(stress.data.recommended as DscrYear[]) ?? []}
              scenarios={stress.data.scenarios ?? []}
              threshold={stress.data.dscr_threshold ?? facts.right_sizing.dscr_threshold}
              stressFloor={stress.data.stress_floor ?? facts.right_sizing.stress_floor}
              language={language}
            />
          </div>
        </Card>
      ),
    },
    facts.amortization_recommended && {
      id: 'repayment',
      label: repayment?.heading ?? strings.schedule,
      node: (
        <Card
          heading={repayment?.heading ?? strings.schedule}
          cites={sourceTitles(repayment?.cites ?? [])}
          strings={strings}
        >
          <Body>{repayment?.body}</Body>
          <div className="mt-5">
            <ScheduleTable
              rows={facts.amortization_recommended.schedule}
              mode={repayment?.data.mode ?? 'serviced'}
              alternateMode={facts.amortization_alternate_mode?.mode ?? null}
              alternateInstalment={facts.amortization_alternate_mode?.instalment ?? null}
              language={language}
              strings={strings}
            />
          </div>
        </Card>
      ),
    },
    marketReach && {
      id: 'market_reach',
      label: marketReach.heading,
      node: (
        <Card
          heading={marketReach.heading}
          cites={sourceTitles(marketReach.cites)}
          strings={strings}
        >
          <Body>{marketReach.body}</Body>
          {marketReach.data.villages && (
            <ul className="mt-4 flex flex-wrap gap-1.5">
              {marketReach.data.villages.map((v) => (
                <li
                  key={v.name}
                  className="tabular rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground"
                >
                  {language === 'hi' && v.name_hi ? v.name_hi : v.name} · {v.distance_km} km
                </li>
              ))}
            </ul>
          )}
        </Card>
      ),
    },
    competition?.data.band && {
      id: 'competition',
      label: competition.heading,
      node: (
        <Card
          heading={competition.heading}
          cites={sourceTitles(competition.cites)}
          strings={strings}
        >
          <Body>{competition.body}</Body>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <BandBar
              band={competition.data.band}
              format={(v) => String(Math.round(Number(v)))}
              label={strings.existingEnterprises}
              language={language}
            />
            {threats?.data.price_band && (
              <BandBar
                band={threats.data.price_band}
                format={(v) => inr(v)}
                label={strings.priceSpread}
                language={language}
              />
            )}
          </div>
        </Card>
      ),
    },
    swot?.data.quadrants && {
      id: 'swot',
      label: swot.heading,
      node: (
        <Card heading={swot.heading} cites={sourceTitles(swot.cites)} strings={strings}>
          <SwotGrid quadrants={swot.data.quadrants} labels={strings.quadrant} />
        </Card>
      ),
    },
    threats && {
      id: 'threats',
      label: threats.heading,
      node: (
        <Card heading={threats.heading} cites={sourceTitles(threats.cites)} strings={strings}>
          <ul className="space-y-3">
            {(threats.data.items ?? []).map((item) => (
              <li key={item.id} className="flex gap-2.5 text-[15px] leading-7">
                <span
                  aria-hidden
                  className="mt-1.5 shrink-0 text-xs"
                  style={{
                    color:
                      item.severity === 'high' ? 'var(--destructive)' : 'var(--warning)',
                  }}
                >
                  ▲
                </span>
                <span className="min-w-0 flex-1 text-muted-foreground max-w-[68ch]">
                  {item.text}{' '}
                  <span className="text-xs uppercase tracking-wide text-subtle-foreground">
                    {item.severity}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          {threats.data.seasonality?.months && (
            <div className="mt-6">
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
        </Card>
      ),
    },
    {
      id: 'scheme',
      label: scheme?.heading ?? strings.apply,
      node: (
        <Card
          heading={scheme?.heading ?? strings.apply}
          cites={sourceTitles(scheme?.cites ?? [])}
          strings={strings}
        >
          <Body>{scheme?.body}</Body>
          <h3 className="mt-6 text-sm font-semibold text-foreground">{strings.documents}</h3>
          <ul className="mt-2.5 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {facts.eligibility.documents.map((doc) => (
              <li key={doc.en} className="flex gap-2 text-sm leading-6 text-muted-foreground">
                <span aria-hidden className="text-subtle-foreground">
                  ☐
                </span>
                {language === 'hi' && doc.hi ? doc.hi : doc.en}
              </li>
            ))}
          </ul>
        </Card>
      ),
    },
  ]

  const sections = entries.filter((e): e is Entry => Boolean(e))
  const navItems: NavItem[] = sections.map(({ id, label }) => ({ id, label }))

  return (
    <div className="mx-auto w-full max-w-[1400px] px-4 py-6 lg:px-8 lg:py-10">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground lg:text-3xl">
            {language === 'hi' && facts.village.name_hi ? facts.village.name_hi : facts.village.name}
            <span className="ml-2 text-base font-normal text-muted-foreground">
              {facts.village.block} · {facts.village.district}
            </span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {language === 'hi' && facts.template.name_hi
              ? facts.template.name_hi
              : facts.template.name}{' '}
            · {facts.scheme.scheme_name}
          </p>
        </div>
        <div className="no-print flex gap-2 lg:hidden">
          <SmallButton onClick={() => window.print()}>{strings.print}</SmallButton>
          <SmallButton onClick={onRestart}>{strings.back}</SmallButton>
        </div>
      </header>

      {facts.contains_synthetic_data && (
        <p
          className="print-block mb-6 rounded-lg px-4 py-3 text-sm leading-6"
          style={{
            background: 'color-mix(in srgb, var(--warning) 18%, var(--background))',
            color: 'var(--foreground)',
          }}
        >
          <strong className="font-semibold">⚠ {strings.synthetic}.</strong> {strings.syntheticNote}
        </p>
      )}

      <div className="report-grid lg:grid lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10 xl:grid-cols-[17rem_minmax(0,1fr)]">
        <ReportNav
          items={navItems}
          facts={facts}
          language={language}
          strings={strings}
          provenanceCount={Object.keys(facts.numeric_index).length}
          onProvenance={() => setProvenanceOpen(true)}
          onRestart={onRestart}
        />

        <div className="min-w-0 space-y-4 lg:space-y-5">
          {sections.map(({ id, node }) => (
            <div key={id} id={id} data-section>
              {node}
            </div>
          ))}

          <button
            type="button"
            onClick={() => setProvenanceOpen(true)}
            className="no-print w-full rounded-lg border border-dashed border-border px-4 py-3 text-sm font-medium text-primary lg:hidden"
          >
            {strings.provenance} ({Object.keys(facts.numeric_index).length})
          </button>

          <footer className="border-t border-border pt-4 text-xs leading-6 text-subtle-foreground">
            <p className="max-w-[80ch]">{section('data_note')?.body}</p>
            <p className="tabular mt-2">
              {validation.checked} {strings.grounded} · {validation.passed ? '✓' : '✗'} ·{' '}
              {strings.narrator}: {report.narrator} ·{' '}
              {lakh(facts.numeric_index.addressable_market_point ?? '0')}{' '}
              {strings.addressableMarket}
            </p>
          </footer>
        </div>
      </div>

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

function Body({ children }: { children?: ReportSection['body'] }) {
  if (!children) return null
  return <p className="max-w-[68ch] text-[15px] leading-7 text-muted-foreground">{children}</p>
}

function Card({
  heading,
  cites,
  strings,
  children,
}: {
  heading: string
  cites: string[]
  strings: Strings
  children: ReactNode
}) {
  return (
    <section className="print-block print-flat rounded-lg border border-border bg-card p-5 sm:p-6">
      <h2 className="text-lg font-semibold tracking-tight text-foreground lg:text-xl">{heading}</h2>
      <div className="mt-3">{children}</div>
      {cites.length > 0 && (
        <p className="mt-4 border-t border-border pt-3 text-[11px] leading-snug text-subtle-foreground">
          {strings.source}: {cites.join(' · ')}
        </p>
      )}
    </section>
  )
}

function SmallButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-border px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
    >
      {children}
    </button>
  )
}
