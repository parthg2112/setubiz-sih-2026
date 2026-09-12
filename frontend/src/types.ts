/** Mirrors the FastAPI response shapes. Money arrives as decimal strings — never parse to a
 *  float for display; only for chart geometry, where a pixel of drift is invisible. */

export type Language = 'en' | 'hi'

export interface VillageMatch {
  shrid: string
  name: string
  name_hi: string | null
  block: string
  district: string
  state: string
  score: number
  reason: string
}

export interface Source {
  id: string
  title: string
  kind: string
  publisher: string | null
  url: string | null
  year: string | null
  synthetic: boolean
  note: string | null
}

export interface Band {
  low: string
  point: string
  high: string
  unit: string
  method: string
  confidence: 'high' | 'medium' | 'low'
  sources: string[]
}

export interface DscrYear {
  year: number
  noi: string
  debt_service: string
  dscr: string
  passes: boolean
}

export interface StressScenario {
  label: string
  min_dscr: string
  passes: boolean
  series: { year: number; dscr: string }[]
}

export interface ScheduleRow {
  quarter: number
  year: number
  phase: 'moratorium' | 'repayment'
  opening: string
  interest: string
  principal: string
  instalment: string
  closing: string
}

export interface SectionData {
  // headline
  catchment_households?: string
  villages_count?: number
  // loan_structure
  max_loan?: string
  recommended_loan?: string
  headroom?: string
  required_capital?: string
  debt_need?: string
  binding?: string
  dscr_threshold?: string
  margin?: string
  project_cost?: string
  scheme_name?: string
  annual_rate_pct?: string
  sca_rate_pct?: string
  tenure_years?: string
  total_quarters?: number
  moratorium_quarters?: number
  max_loan_min_dscr?: string
  recommended_min_dscr?: string
  monthly_revenue?: string
  monthly_opex?: string
  monthly_net?: string
  // stress
  stress_floor?: string
  annual_noi?: string
  annual_noi_stress_15?: string
  annual_noi_stress_30?: string
  recommended_stress_dscr_15?: string
  max_loan_stress_dscr_15?: string
  recommended?: DscrYear[] | ScheduleRow[]
  scenarios?: StressScenario[]
  // repayment
  mode?: string
  quarterly_instalment?: string
  total_interest?: string
  quarterly_instalment_max?: string
  total_interest_max?: string
  repayment_quarters?: number
  alternate_mode?: string | null
  alternate_instalment?: string | null
  // market_reach
  households_2011?: string
  population_2011?: string
  households_now?: string
  population_now?: string
  growth_factor?: string
  villages_with_bank?: number
  road_connected_pct?: string
  mandis_in_radius?: number
  demand_per_household_low?: string
  demand_per_household_high?: string
  addressable_market_low?: string
  addressable_market_high?: string
  addressable_market_point?: string
  villages?: VillageDot[]
  income_segments?: { label: string; share: string; households: number }[]
  // competition
  band?: Band
  observed_osm?: number
  z_score?: number
  estimator?: string
  // scheme
  logic?: string
  verdict?: 'eligible' | 'eligible_with_conditions' | 'ineligible'
  corporation_name?: string | null
  corporation_name_hi?: string | null
  annual_family_income?: string | null
  income_ceiling?: string | null
  income_status?: 'provided' | 'missing'
  sca?: { name: string; name_hi: string | null; address: string; channel: string } | null
  // threats
  items?: { id: string; severity: string; text: string }[]
  price_band?: Band | null
  seasonality?: {
    commodity?: string
    market?: string
    months?: string[]
    arrivals?: number[]
    modal_price?: number[]
    cv?: string
    peak_month?: string
    trough_month?: string
  }
  // swot
  quadrants?: Record<string, string[]>
  rules_fired?: string[]
  // alternatives
  unit_label?: string
  base_units?: number
  unit_range?: [number, number]
  unit_step?: number
  category?: string
  configurations?: AltConfiguration[]
  considered?: {
    units: number
    project_cost: string
    shortfall: string
    funded: boolean
  }[]
  // group
  members?: {
    index: number
    name: string | null
    social_category: string
    contribution: string
    liability: string
    corporation: string | null
    verdict: string
    qualifies: boolean
  }[]
  pooled_margin?: string
  liability_split?: string
  mixed_categories?: boolean
  routing_policy?: string | null
  all_qualify?: boolean
  // stacking
  combinable?: SchemeCombination[]
  needs_verification?: SchemeCombination[]
  mutually_exclusive?: SchemeCombination[]
  closest_units?: number | null
  additional_margin_needed?: string | null
  phased?: {
    start_units: number
    target_units: number
    expansion_cost: string
    annual_retained: string
    years_to_expand: number
  } | null
}

/** One village bubble on the catchment map. */
export interface VillageDot {
  name: string
  name_hi: string | null
  distance_km: number
  households_2011: number
  lat: number
  lon: number
  has_bank?: boolean
}

export interface SchemeCombination {
  schemes: string[]
  names: string[]
  reason: string
  source: string | null
  sequencing: string | null
  combined_cap: string | null
  subsidy_delta_pct: string | null
}

export interface AltConfiguration {
  units: number
  project_cost: string
  loan: string
  instalment: string
  min_dscr: string
  comfort: 'comfortable' | 'tight'
  self_financed: boolean
}

export interface ReportSection {
  id: string
  heading: string
  body: string
  cites: string[]
  data: SectionData
}

export interface Report {
  language: Language
  narrator: string
  sections: ReportSection[]
}

export interface ValidationReport {
  passed: boolean
  checked: number
  ungrounded: { text: string; value: string; context: string }[]
  notes: string[]
}

export interface EligibilityDoc {
  en: string
  hi: string | null
}

/** Engine advisories carry both languages so the report never mixes them. */
export interface Advisory {
  id: string
  text_en: string
  text_hi: string
}

export interface Facts {
  generated_at: string
  village: {
    shrid: string
    name: string
    name_hi: string | null
    block: string
    district: string
    state: string
  }
  template: { id: string; name: string; name_hi: string | null; unit: string; source: string }
  scheme: {
    logic: string
    scheme_name: string
    margin: string
    project_cost: string
    max_loan: string
    annual_rate: string
    total_quarters: number
    moratorium_quarters: number
    sca_rate: string | null
    referrals: string[]
    notes: string[]
  }
  right_sizing: {
    max_loan: string
    recommended_loan: string
    headroom: string
    binding: string
    required_capital: string
    debt_need: string
    capital_shortfall: string
    dscr_threshold: string
    stress_floor: string
    max_loan_min_dscr: string
    recommended_min_dscr: string
    max_loan_dscr: DscrYear[]
    recommended_dscr: DscrYear[]
    warnings: Advisory[]
  }
  amortization_max: { instalment: string; total_interest: string; schedule: ScheduleRow[] } | null
  amortization_recommended: {
    instalment: string
    total_interest: string
    schedule: ScheduleRow[]
  } | null
  amortization_alternate_mode: { mode: string; instalment: string } | null
  eligibility: {
    verdict: 'eligible' | 'eligible_with_conditions' | 'ineligible'
    corporation: { id: string; name: string; name_hi: string | null; portal: string } | null
    social_category: string
    annual_family_income: string | null
    income_ceiling: string | null
    reasons: string[]
    reasons_hi?: string[]
    conditions: string[]
    conditions_hi?: string[]
    documents: EligibilityDoc[]
    sca: { name: string; name_hi: string | null; address: string; channel: string } | null
    comparison: {
      id: string
      name: string
      name_hi: string | null
      ministry: string
      loan_range: [string, string]
      collateral_free: boolean
      highlights: string[]
      when_to_prefer: string
      when_to_prefer_hi?: string
      portal: string
    }[]
  }
  numeric_index: Record<string, string>
  provenance: Record<string, string[]>
  sources: Source[]
  warnings: Advisory[]
  contains_synthetic_data: boolean
}

export interface AdvisoryResponse {
  facts: Facts
  report: Report
  validation: ValidationReport
}

export interface CostTemplate {
  id: string
  name: string
  name_hi: string | null
  category: string
  unit: string
  required_capital: string
  annual_noi: string
}
