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
  // loan_structure
  max_loan?: string
  recommended_loan?: string
  headroom?: string
  required_capital?: string
  debt_need?: string
  binding?: string
  dscr_threshold?: string
  // stress
  stress_floor?: string
  recommended?: DscrYear[] | ScheduleRow[]
  scenarios?: StressScenario[]
  // repayment
  mode?: string
  alternate_mode?: string | null
  alternate_instalment?: string | null
  // market_reach
  villages?: { name: string; name_hi: string | null; distance_km: number; households_2011: number }[]
  income_segments?: { label: string; share: string; households: number }[]
  // competition
  band?: Band
  observed_osm?: number
  estimator?: string
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
    reasons: string[]
    conditions: string[]
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
