import { BandBar } from './BandBar'
import { CatchmentMap } from './CatchmentMap'
import { DistanceBands, IncomeSegments } from './DistanceBands'
import { DscrChart } from './DscrChart'
import { LoanComparison } from './LoanComparison'
import { PrintHeader } from './PrintHeader'
import { ScheduleTable } from './ScheduleTable'
import { SeasonalityChart } from './SeasonalityChart'
import { SwotGrid } from './SwotGrid'
import { StatRows } from './StatRows'
import { inr, lakh, ratio, type Strings } from '../format'
import type { AdvisoryResponse, DscrYear, Language } from '../types'
import type { AdvisoryInput } from '../api'

interface Props {
  data: AdvisoryResponse
  input: AdvisoryInput | null
  language: Language
  strings: Strings
}

/** The printed sheet, ordered exactly as the problem statement numbers its requirements.
 *
 *  On screen the answer leads and the reasoning folds away, which is the right shape for a
 *  decision. On paper the reader is a judge or a bank officer checking the service against its
 *  brief, so the document follows the brief's own hierarchy: Module 1 with the six parameters in
 *  the PS's order and under the PS's names, then Module 2 with the margin rule, the scheme
 *  router and the repayment generator, and only then the appraisal that goes beyond the formula.
 *  Everything in this tree is print-only; the screen never shows it. */
export function PrintReport({ data, input, language, strings }: Props) {
  const hi = language === 'hi'
  const { facts, report } = data
  const section = (id: string) => report.sections.find((s) => s.id === id)
  const num = (id: string) => facts.numeric_index[id]
  const stat = (id: string, fmt?: (v: string) => string) => {
    const raw = num(id)
    return raw === undefined ? undefined : fmt ? fmt(raw) : raw
  }
  const locale = hi ? 'hi-IN' : 'en-IN'
  const int = (v: string) => Math.round(Number(v)).toLocaleString(locale)
  const villageName = hi && facts.village.name_hi ? facts.village.name_hi : facts.village.name
  const marketReach = section('market_reach')
  const competition = section('competition')
  const swot = section('swot')
  const threats = section('threats')
  const outOfScope = Number(facts.right_sizing.max_loan) <= 0

  return (
    <div className="setubiz-print-only setubiz-print-doc">
      <PrintHeader facts={facts} input={input} language={language} strings={strings} />

      {/* ---------------- Module 1: the six parameters, in the PS's order ---------------- */}
      <h2 className="setubiz-print-module">{strings.printModule1}</h2>

      <h3 className="setubiz-print-param">{strings.psMarketReach}</h3>
      {marketReach && (
        <div className="setubiz-print-block">
          {marketReach.body && <p className="ux4g-body-m-default setubiz-measure">{marketReach.body}</p>}
          {marketReach.data.villages && marketReach.data.villages.length > 0 && (
            <>
              {(() => {
                const centre = marketReach.data.villages.reduce((a, b) =>
                  b.distance_km < a.distance_km ? b : a,
                )
                return (
                  <CatchmentMap
                    centreName={villageName}
                    centre={{ lat: centre.lat, lon: centre.lon }}
                    villages={marketReach.data.villages}
                    radiusKm={input?.radius_km ?? 10}
                    language={language}
                    strings={strings}
                  />
                )
              })()}
              <div className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-2 ux4g-gap-l ux4g-mt-m">
                <DistanceBands
                  villages={marketReach.data.villages}
                  radiusKm={input?.radius_km ?? 10}
                  language={language}
                />
                {marketReach.data.income_segments && (
                  <IncomeSegments segments={marketReach.data.income_segments} language={language} />
                )}
              </div>
              <div className="ux4g-mt-m">
                <StatRows
                  columns={3}
                  rows={[
                    { label: strings.statCatchment, value: stat('households_now', int) },
                    { label: strings.statPopulationNow, value: stat('population_now', int) },
                    { label: strings.statVillages, value: stat('villages_in_radius', int) },
                    { label: strings.statBankVillages, value: stat('villages_with_bank') },
                    { label: strings.statRoadPct, value: stat('road_connected_pct', (v) => `${Number(v)}%`) },
                    { label: strings.statMandis, value: stat('mandis_in_radius') },
                  ]}
                />
              </div>
            </>
          )}
        </div>
      )}

      <h3 className="setubiz-print-param">{strings.psOpportunity}</h3>
      <div className="setubiz-print-block">
        <StatRows
          columns={3}
          rows={[
            {
              label: strings.statDemandPerHH,
              value:
                num('demand_per_household_low') !== undefined
                  ? `${inr(num('demand_per_household_low')!)} - ${inr(num('demand_per_household_high')!)}`
                  : undefined,
            },
            {
              label: strings.statAddressable,
              value:
                num('addressable_market_low') !== undefined
                  ? `${lakh(num('addressable_market_low')!)} - ${lakh(num('addressable_market_high')!)}`
                  : undefined,
            },
            { label: 'Demand-supply ratio', value: stat('demand_supply_ratio', ratio) },
            { label: strings.printHouseholdsPer, value: stat('households_per_competitor', ratio) },
          ]}
        />
        {section('headline')?.body && (
          <p className="ux4g-body-m-default setubiz-measure ux4g-mt-s">{section('headline')?.body}</p>
        )}
      </div>

      <h3 className="setubiz-print-param">{strings.psSwot}</h3>
      {swot?.data.quadrants && (
        <div className="setubiz-print-block">
          <SwotGrid quadrants={swot.data.quadrants} labels={strings.quadrant} />
        </div>
      )}

      <h3 className="setubiz-print-param">{strings.psThreats}</h3>
      <div className="setubiz-print-block">
        {(threats?.data.items ?? []).length > 0 && (
          <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
            {(threats?.data.items ?? []).map((item) => (
              <li className="ux4g-d-flex ux4g-ai-start ux4g-gap-x-s" key={item.id}>
                <span
                  className={`ux4g-tag-s ${
                    item.severity === 'high' ? 'ux4g-tag-tonal-error' : 'ux4g-tag-tonal-warning'
                  }`}
                >
                  {item.severity}
                </span>
                <span className="ux4g-body-m-default setubiz-measure">{item.text}</span>
              </li>
            ))}
          </ul>
        )}
        {threats?.data.seasonality?.months && (
          <div className="ux4g-mt-m">
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
      </div>

      <h3 className="setubiz-print-param">{strings.psCompetitors}</h3>
      {competition?.data.band && (
        <div className="setubiz-print-block">
          <BandBar
            band={competition.data.band}
            format={(v) => String(Math.round(Number(v)))}
            label={strings.existingEnterprises}
            language={language}
          />
          <div className="ux4g-mt-m">
            <StatRows
              columns={3}
              rows={[
                { label: strings.printDensity, value: stat('competitor_density_per_1k_households', ratio) },
                { label: strings.printHouseholdsPer, value: stat('households_per_competitor', ratio) },
                { label: 'OpenStreetMap', value: competition.data.observed_osm !== undefined ? String(competition.data.observed_osm) : undefined },
              ]}
            />
          </div>
          {competition.body && (
            <p className="ux4g-body-m-default setubiz-measure ux4g-mt-s">{competition.body}</p>
          )}
        </div>
      )}

      <h3 className="setubiz-print-param">{strings.psPrice}</h3>
      <div className="setubiz-print-block">
        {threats?.data.price_band && (
          <BandBar
            band={threats.data.price_band}
            format={(v) => inr(v)}
            label={strings.priceSpread}
            language={language}
          />
        )}
        <div className="ux4g-mt-m">
          <StatRows
            columns={3}
            rows={[
              {
                label: strings.statDemandPerHH,
                value:
                  num('demand_per_household_low') !== undefined
                    ? `${inr(num('demand_per_household_low')!)} - ${inr(num('demand_per_household_high')!)}`
                    : undefined,
              },
              { label: strings.statMonthlyRevenue, value: stat('monthly_revenue', inr) },
              { label: strings.statMonthlyOpex, value: stat('monthly_opex', inr) },
            ]}
          />
        </div>
      </div>

      {/* ---------------- Module 2: calculator and router, in the PS's own table order --------- */}
      <h2 className="setubiz-print-module">{strings.printModule2}</h2>

      <table className="ux4g-table setubiz-print-rules setubiz-print-block">
        <thead>
          <tr>
            <th scope="col">{hi ? 'वित्तीय पैरामीटर' : 'Financial parameter'}</th>
            <th scope="col">{strings.printRuleCol}</th>
            <th scope="col">{strings.printValueCol}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">{strings.printMarginRow}</th>
            <td>{hi ? '10% अंशदान (आवेदक की बचत)' : '10% promoter contribution (applicant savings)'}</td>
            <td className="setubiz-tabular">{inr(facts.scheme.margin)}</td>
          </tr>
          <tr>
            <th scope="row">{hi ? 'कुल परियोजना लागत' : 'Total project cost'}</th>
            <td>{hi ? 'मार्जिन ÷ 10%' : 'Margin ÷ 10%'}</td>
            <td className="setubiz-tabular">{inr(facts.scheme.project_cost)}</td>
          </tr>
          <tr>
            <th scope="row">{hi ? 'अधिकतम ऋण' : 'Maximum loan'}</th>
            <td>{hi ? 'परियोजना लागत का 90%, योजना सीमा तक' : '90% of project cost, up to the scheme cap'}</td>
            <td className="setubiz-tabular">{inr(facts.scheme.max_loan)}</td>
          </tr>
          <tr>
            <th scope="row">{strings.printLogicRow}</th>
            <td>
              {facts.scheme.logic === 'A'
                ? hi
                  ? 'लॉजिक A: 6.5% वार्षिक, 3 वर्ष, 3-माह अधिस्थगन'
                  : 'Logic A: 6.5% p.a., 3-year tenure, 3-month moratorium'
                : facts.scheme.logic === 'B'
                  ? hi
                    ? 'लॉजिक B: 8.0% वार्षिक, 7 वर्ष, 6-माह अधिस्थगन'
                    : 'Logic B: 8.0% p.a., 7-year tenure, 6-month moratorium'
                  : hi
                    ? 'स्कीम दायरे से बाहर'
                    : 'out of scheme scope'}
            </td>
            <td className="setubiz-tabular">{facts.scheme.scheme_name}</td>
          </tr>
          <tr>
            <th scope="row">{hi ? 'चुकौती जनरेटर' : 'Repayment generator'}</th>
            <td>{hi ? 'तिमाही अनुसूची, अधिस्थगन-सजग, कार्यशील पूँजी सहित' : 'quarterly schedule, moratorium-aware, working capital included'}</td>
            <td className="setubiz-tabular">
              {facts.amortization_recommended
                ? `${inr(facts.amortization_recommended.instalment)} / ${hi ? 'तिमाही' : 'quarter'}`
                : hi
                  ? 'लागू नहीं'
                  : 'not applicable'}
            </td>
          </tr>
        </tbody>
      </table>

      <h3 className="setubiz-print-param">{strings.printAppraisal}</h3>
      {!outOfScope && (
        <div className="setubiz-print-block">
          <LoanComparison
            maxLoan={facts.scheme.max_loan}
            recommendedLoan={facts.right_sizing.recommended_loan}
            headroom={facts.right_sizing.headroom}
            requiredCapital={facts.right_sizing.required_capital}
            debtNeed={facts.right_sizing.debt_need}
            binding={facts.right_sizing.binding}
            maxMinDscr={facts.right_sizing.max_loan_min_dscr}
            recommendedMinDscr={facts.right_sizing.recommended_min_dscr}
            dscrThreshold={facts.right_sizing.dscr_threshold}
            language={language}
            strings={strings}
          />
          {section('stress')?.data.recommended && (
            <div className="ux4g-mt-l">
              <DscrChart
                base={(section('stress')!.data.recommended as DscrYear[]) ?? []}
                scenarios={section('stress')!.data.scenarios ?? []}
                threshold={facts.right_sizing.dscr_threshold}
                stressFloor={facts.right_sizing.stress_floor}
                language={language}
              />
            </div>
          )}
          {section('repayment') && facts.amortization_recommended && (
            <div className="ux4g-mt-l">
              <ScheduleTable
                rows={facts.amortization_recommended.schedule}
                mode={section('repayment')!.data.mode ?? 'serviced'}
                alternateMode={facts.amortization_alternate_mode?.mode ?? null}
                alternateInstalment={facts.amortization_alternate_mode?.instalment ?? null}
                language={language}
                strings={strings}
              />
            </div>
          )}
        </div>
      )}

      {facts.warnings.length > 0 && (
        <div className="setubiz-print-block setubiz-mt-m">
          <h3 className="setubiz-print-param">{strings.warningsHeading}</h3>
          <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
            {facts.warnings.map((w) => (
              <li className="ux4g-body-m-default setubiz-measure" key={w.id}>
                {hi ? w.text_hi : w.text_en}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ---------------- Sources: the judge's "where did that number come from" answer ---------- */}
      <h3 className="setubiz-print-param">{strings.printSources}</h3>
      <ol className="ux4g-body-s-default ux4g-text-neutral-secondary setubiz-print-sources">
        {facts.sources.map((s) => (
          <li key={s.id}>
            {s.title}
            {s.publisher ? ` · ${s.publisher}` : ''}
            {s.year ? ` · ${s.year}` : ''}
          </li>
        ))}
      </ol>
      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary setubiz-measure setubiz-mt-m">
        {section('data_note')?.body}
      </p>
    </div>
  )
}
