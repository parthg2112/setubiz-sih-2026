import { useEffect, useId, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { BandBar } from '../components/BandBar'
import { DscrChart } from '../components/DscrChart'
import { LoanComparison } from '../components/LoanComparison'
import { OutOfScope } from '../components/OutOfScope'
import { ProvenancePanel } from '../components/ProvenancePanel'
import { ScheduleTable } from '../components/ScheduleTable'
import { SchemeStacking } from '../components/SchemeStacking'
import { WhatIf } from '../components/WhatIf'
import { SizesThatWork } from '../components/SizesThatWork'
import { SeasonalityChart } from '../components/SeasonalityChart'
import { SwotGrid } from '../components/SwotGrid'
import { inr, lakh, type Strings } from '../format'
import type { AdvisoryResponse, DscrYear, Language } from '../types'
import { fromSearchParams } from '../urlState'

interface Props {
  language: Language
  strings: Strings
  onBusyChange: (busy: boolean) => void
  onRestart: () => void
}

type State =
  | { kind: 'loading' }
  | { kind: 'ready'; data: AdvisoryResponse }
  | { kind: 'error'; message: string }
  | { kind: 'invalid' }

export function Report({ language, strings, onBusyChange, onRestart }: Props) {
  const [params] = useSearchParams()
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)

  const input = fromSearchParams(params, language)
  // Re-run whenever the inputs or the language change. Serialising the input is what lets this
  // effect depend on the *values* rather than on a new object identity every render.
  const key = input ? JSON.stringify(input) : null

  useEffect(() => {
    if (!key) {
      setState({ kind: 'invalid' })
      return
    }
    let live = true
    setState({ kind: 'loading' })
    onBusyChange(true)
    api
      .advisory(JSON.parse(key))
      .then((data) => live && setState({ kind: 'ready', data }))
      .catch((e: unknown) =>
        live && setState({ kind: 'error', message: e instanceof Error ? e.message : String(e) }),
      )
      .finally(() => live && onBusyChange(false))
    return () => {
      live = false
    }
  }, [key, attempt, onBusyChange])

  if (state.kind === 'invalid') {
    return (
      <Centred>
        <div className="ux4g-empty-state">
          <span className="ux4g-icon-outlined ux4g-empty-state-icon ux4g-text-primary" aria-hidden="true">
            link_off
          </span>
          <div className="ux4g-empty-state-content">
            <h1 className="ux4g-title-l-strong">{strings.reportGoneTitle}</h1>
            <p className="ux4g-body-l-default setubiz-measure">{strings.reportGoneBody}</p>
          </div>
          <Link className="ux4g-btn ux4g-btn-tonal-primary ux4g-btn-lg" to="/">
            {strings.newReport}
          </Link>
        </div>
      </Centred>
    )
  }

  if (state.kind === 'loading') {
    return (
      <Centred>
        <div className="ux4g-d-flex ux4g-flex-column ux4g-ai-center ux4g-gap-y-m" role="status">
          <span className="ux4g-spinner ux4g-spinner-xl" aria-hidden="true" />
          <p className="ux4g-body-l-default">{strings.loadingReport}</p>
        </div>
      </Centred>
    )
  }

  if (state.kind === 'error') {
    return (
      <Centred>
        <div className="ux4g-empty-state">
          <span className="ux4g-icon-outlined ux4g-empty-state-icon ux4g-text-primary" aria-hidden="true">
            error_outline
          </span>
          <div className="ux4g-empty-state-content">
            <h1 className="ux4g-title-l-strong">{strings.loadFailed}</h1>
            <p className="ux4g-body-l-default setubiz-measure">{state.message}</p>
          </div>
          <div className="ux4g-d-flex ux4g-gap-x-s">
            <button
              type="button"
              className="ux4g-btn ux4g-btn-primary ux4g-btn-lg"
              onClick={() => setAttempt(attempt + 1)}
            >
              {strings.tryAgain}
            </button>
            <button
              type="button"
              className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
              onClick={onRestart}
            >
              {strings.newReport}
            </button>
          </div>
        </div>
      </Centred>
    )
  }

  return <Loaded data={state.data} language={language} strings={strings} onRestart={onRestart} />
}

function Centred({ children }: { children: ReactNode }) {
  return <div className="ux4g-container ux4g-py-2xl">{children}</div>
}

function Loaded({
  data,
  language,
  strings,
  onRestart,
}: {
  data: AdvisoryResponse
  language: Language
  strings: Strings
  onRestart: () => void
}) {
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
  const alternatives = section('alternatives')
  const stacking = section('stacking')


  /* The scheme cannot fund this applicant: project cost outside the envelope, or no loan size
     that services. Backend signals it with max_loan 0 plus a referral list. */
  const outOfScope = Number(facts.right_sizing.max_loan) <= 0

  const sourceTitles = (cites: string[]) =>
    cites.map((id) => facts.sources.find((s) => s.id === id)?.title).filter(Boolean) as string[]

  const villageName =
    language === 'hi' && facts.village.name_hi ? facts.village.name_hi : facts.village.name
  const templateName =
    language === 'hi' && facts.template.name_hi ? facts.template.name_hi : facts.template.name

  return (
    <div className="ux4g-container ux4g-py-l">
      <nav className="ux4g-breadcrumb setubiz-no-print" aria-label={strings.contents}>
        <ol className="ux4g-breadcrumb-list">
          <li className="ux4g-breadcrumb-item">
            <Link className="ux4g-breadcrumb-link" to="/">
              {strings.home}
            </Link>
            <span className="ux4g-breadcrumb-divider" aria-hidden="true">
              /
            </span>
          </li>
          <li className="ux4g-breadcrumb-item" aria-current="page">
            {strings.yourReport}
          </li>
        </ol>
      </nav>

      <header className="ux4g-d-flex ux4g-jc-between ux4g-ai-start ux4g-flex-wrap ux4g-gap-m ux4g-mt-m">
        <div>
          <h1 className="ux4g-heading-xl-strong">{villageName}</h1>
          <p className="ux4g-body-l-default ux4g-text-neutral-secondary">
            {facts.village.block} · {facts.village.district} · {templateName}
          </p>
        </div>
        <div className="ux4g-d-flex ux4g-gap-x-s setubiz-no-print">
          <button
            type="button"
            className="ux4g-btn ux4g-btn-tonal-primary ux4g-btn-lg ux4g-gap-x-xs"
            onClick={() => window.print()}
          >
            <span className="ux4g-icon-outlined" aria-hidden="true">
              print
            </span>
            {strings.print}
          </button>
          <button
            type="button"
            className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
            onClick={onRestart}
          >
            {strings.newReport}
          </button>
        </div>
      </header>

      {facts.contains_synthetic_data ? (
        <div className="ux4g-alert ux4g-alert-warning ux4g-mt-l setubiz-print-block" role="status">
          <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
            warning
          </span>
          <div className="ux4g-alert-content">
            <p className="ux4g-alert-title">{strings.synthetic}</p>
            <p className="ux4g-alert-message setubiz-measure">{strings.syntheticNote}</p>
          </div>
        </div>
      ) : (
        <div className="ux4g-alert ux4g-alert-info ux4g-mt-l setubiz-print-block" role="status">
          <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
            verified
          </span>
          <div className="ux4g-alert-content">
            <p className="ux4g-alert-title">{strings.officialData}</p>
            <p className="ux4g-alert-message setubiz-measure">{strings.officialDataNote}</p>
          </div>
        </div>
      )}

      {/* ---- The answer. One number, one reason, before anything that justifies it.
              When the scheme cannot fund this applicant at all the backend returns max_loan 0 and
              a referral list, and a comparison of two zeroes is worse than useless — it reads as
              an approval. That case gets its own screen instead. ---- */}
      {outOfScope ? (
        <OutOfScope facts={facts} language={language} strings={strings} />
      ) : (
        loan?.data.max_loan && (
        <section className="ux4g-mt-l setubiz-print-block" id="answer" data-section>
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
        </section>
        )
      )}

      {/* ---- What actually works. Shown whenever the engine found something to say: either
              sizes that fit, or an honest account of why none does. ---- */}
      {!outOfScope && alternatives && (
        <SizesThatWork data={alternatives.data} language={language} strings={strings} />
      )}

      {/* ---- Warnings. Never collapsed: these are the reasons someone defaults. ---- */}
      {!outOfScope && facts.warnings.length > 0 && (
        <section className="ux4g-mt-l setubiz-print-block" aria-labelledby="warnings-heading">
          <h2 className="ux4g-heading-m-strong ux4g-mb-s" id="warnings-heading">
            {strings.warningsHeading}
          </h2>
          <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
            {facts.warnings.map((w) => (
              <div className="ux4g-alert ux4g-alert-warning" key={w.id}>
                <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
                  priority_high
                </span>
                <div className="ux4g-alert-content">
                  <p className="ux4g-alert-message setubiz-measure">
                    {language === 'hi' ? w.text_hi : w.text_en}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ---- Eligibility. The second thing a reader needs: can I actually apply, and where. ---- */}
      <section className="ux4g-card ux4g-card-outline ux4g-mt-l setubiz-print-block" id="scheme" data-section>
        <div className="ux4g-card-header">
          <h2 className="ux4g-heading-m-strong ux4g-card-title">
            {scheme?.heading ?? strings.apply}
          </h2>
        </div>
        <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
          {scheme?.body && <p className="ux4g-body-l-default setubiz-measure">{scheme.body}</p>}

          <div>
            <h3 className="ux4g-title-s-strong ux4g-mb-s">{strings.documents}</h3>
            <ul className="ux4g-list ux4g-list-default ux4g-list-m">
              {facts.eligibility.documents.map((doc) => (
                <li className="ux4g-list-item" key={doc.en}>
                  <div className="ux4g-list-item-row">
                    <span className="ux4g-list-item-start ux4g-d-flex ux4g-ai-center ux4g-gap-x-s">
                      <span className="ux4g-icon-outlined ux4g-text-neutral-tertiary" aria-hidden="true">
                        check_box_outline_blank
                      </span>
                      <span className="ux4g-body-l-default">
                        {language === 'hi' && doc.hi ? doc.hi : doc.en}
                      </span>
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {facts.eligibility.sca && (
            <div>
              <h3 className="ux4g-title-s-strong ux4g-mb-xs">{strings.apply}</h3>
              <p className="ux4g-body-l-default setubiz-measure">
                {language === 'hi' && facts.eligibility.sca.name_hi
                  ? facts.eligibility.sca.name_hi
                  : facts.eligibility.sca.name}
                <br />
                {facts.eligibility.sca.address}
                <br />
                {facts.eligibility.sca.channel}
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Sliders sit under the answer, labelled so a hypothetical never reads as the
              applicant's own figures. Recompute touches only the finance endpoint. */}
      {!outOfScope && alternatives?.data.unit_range && (
        <WhatIf
          margin={Number(facts.scheme.margin)}
          category={alternatives.data.category ?? ''}
          baseUnits={alternatives.data.base_units ?? 1}
          unitLabel={alternatives.data.unit_label ?? ''}
          unitRange={alternatives.data.unit_range}
          unitStep={alternatives.data.unit_step ?? 1}
          strings={strings}
        />
      )}

      {stacking && <SchemeStacking data={stacking.data} strings={strings} />}

      {/* ---- Everything that explains the answer, opened on demand. ---- */}
      <h2 className="ux4g-heading-m-strong ux4g-mt-xl ux4g-mb-s">{strings.whyThis}</h2>
      <div className="ux4g-accordion ux4g-accordion-bordered">
        {headline && (
          <Panel title={headline.heading} cites={sourceTitles(headline.cites)} strings={strings}>
            <Prose>{headline.body}</Prose>
          </Panel>
        )}

        {!outOfScope && loan && (
          <Panel title={loan.heading} cites={sourceTitles(loan.cites)} strings={strings}>
            <Prose>{loan.body}</Prose>
          </Panel>
        )}

        {!outOfScope && stress?.data.recommended && (
          <Panel
            // No gloss appended: the backend heading is already "What happens in a bad year", so
            // `dscrGloss` would have said the same thing twice in one title.
            title={stress.heading}
            cites={sourceTitles(stress.cites)}
            strings={strings}
          >
            <Prose>{stress.body}</Prose>
            <DscrChart
              base={(stress.data.recommended as DscrYear[]) ?? []}
              scenarios={stress.data.scenarios ?? []}
              threshold={stress.data.dscr_threshold ?? facts.right_sizing.dscr_threshold}
              stressFloor={stress.data.stress_floor ?? facts.right_sizing.stress_floor}
              language={language}
            />
          </Panel>
        )}

        {!outOfScope && facts.amortization_recommended && (
          <Panel
            title={repayment?.heading ?? strings.schedule}
            cites={sourceTitles(repayment?.cites ?? [])}
            strings={strings}
          >
            <Prose>{repayment?.body}</Prose>
            <ScheduleTable
              rows={facts.amortization_recommended.schedule}
              mode={repayment?.data.mode ?? 'serviced'}
              alternateMode={facts.amortization_alternate_mode?.mode ?? null}
              alternateInstalment={facts.amortization_alternate_mode?.instalment ?? null}
              language={language}
              strings={strings}
            />
          </Panel>
        )}

        {marketReach && (
          <Panel
            title={marketReach.heading}
            cites={sourceTitles(marketReach.cites)}
            strings={strings}
          >
            <Prose>{marketReach.body}</Prose>
            {marketReach.data.villages && (
              <ul className="ux4g-d-flex ux4g-flex-wrap ux4g-gap-xs ux4g-mt-m">
                {marketReach.data.villages.map((v) => (
                  <li key={v.name}>
                    <span className="ux4g-tag-tonal-neutral ux4g-tag-s setubiz-tabular">
                      {language === 'hi' && v.name_hi ? v.name_hi : v.name} · {v.distance_km}{' '}
                      {strings.km}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        )}

        {competition?.data.band && (
          <Panel
            title={competition.heading}
            cites={sourceTitles(competition.cites)}
            strings={strings}
          >
            <Prose>{competition.body}</Prose>
            <div className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-2 ux4g-gap-m ux4g-mt-m">
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
          </Panel>
        )}

        {!outOfScope && swot?.data.quadrants && (
          <Panel title={swot.heading} cites={sourceTitles(swot.cites)} strings={strings}>
            <SwotGrid quadrants={swot.data.quadrants} labels={strings.quadrant} />
          </Panel>
        )}

        {threats && (threats.data.items ?? []).length > 0 && (
          <Panel title={threats.heading} cites={sourceTitles(threats.cites)} strings={strings}>
            <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
              {(threats.data.items ?? []).map((item) => (
                <li className="ux4g-d-flex ux4g-ai-start ux4g-gap-x-s" key={item.id}>
                  <span
                    className={`ux4g-tag-tonal-${
                      item.severity === 'high' ? 'error' : 'warning'
                    } ux4g-tag-s`}
                  >
                    {item.severity}
                  </span>
                  <span className="ux4g-body-l-default setubiz-measure">{item.text}</span>
                </li>
              ))}
            </ul>
            {/* Real AGMARKNET data carries no series — data.gov.in publishes only the current day —
                so this chart appears on sample data and is correctly absent on live data. */}
            {threats.data.seasonality?.months && (
              <div className="ux4g-mt-l">
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
          </Panel>
        )}
      </div>

      <div className="ux4g-mt-l setubiz-no-print">
        <button
          type="button"
          className="ux4g-btn ux4g-btn-outline-primary ux4g-btn-lg ux4g-gap-x-xs"
          onClick={() => setProvenanceOpen(true)}
        >
          <span className="ux4g-icon-outlined" aria-hidden="true">
            fact_check
          </span>
          {strings.provenance} ({Object.keys(facts.numeric_index).length})
        </button>
      </div>

      <footer className="ux4g-mt-xl">
        <div className="ux4g-divider-horizontal" />
        <p className="ux4g-body-s-default ux4g-text-neutral-tertiary setubiz-measure ux4g-mt-m">
          {section('data_note')?.body}
        </p>
        <p className="ux4g-body-s-default ux4g-text-neutral-tertiary setubiz-tabular ux4g-mt-s">
          {validation.checked} {strings.grounded} · {strings.narrator}: {report.narrator} ·{' '}
          {lakh(facts.numeric_index.addressable_market_point ?? '0')} {strings.addressableMarket}
        </p>
      </footer>

      <ProvenancePanel
        facts={facts}
        open={provenanceOpen}
        onClose={() => setProvenanceOpen(false)}
        language={language}
        closeLabel={strings.close}
        title={strings.provenanceGloss}
      />
    </div>
  )
}

function Prose({ children }: { children?: string }) {
  if (!children) return null
  return <p className="ux4g-body-l-default setubiz-measure">{children}</p>
}

/** One accordion section.
 *
 *  Open state is held in React rather than handed to the UX4G runtime: the component contract puts
 *  application state on the application, and letting an external script mutate classes on
 *  React-rendered nodes invites them to disagree on the next render. The classes are the system's;
 *  only the toggling is ours. */
function Panel({
  title,
  cites,
  strings,
  children,
}: {
  title: string
  cites: string[]
  strings: Strings
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const id = useId()
  const panelId = `${id}-panel`

  return (
    <div className="ux4g-accordion__item setubiz-print-block">
      <h3 className="ux4g-accordion__header">
        <button
          type="button"
          className={`ux4g-accordion__button${open ? '' : ' collapsed'}`}
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen(!open)}
        >
          <span className="ux4g-accordion__button-content">
            <span className="ux4g-accordion__title">{title}</span>
          </span>
        </button>
      </h3>
      <div className={`ux4g-accordion__collapse${open ? ' show' : ''}`} id={panelId}>
        <div className="ux4g-accordion__body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
          {children}
          {cites.length > 0 && (
            <p className="ux4g-body-s-default ux4g-text-neutral-tertiary">
              {strings.source}: {cites.join(' · ')}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
