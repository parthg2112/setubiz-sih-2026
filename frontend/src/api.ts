import type { AdvisoryResponse, CostTemplate, Language, VillageMatch } from './types'

const BASE = '/api/v1'

async function get<T>(
  path: string,
  params?: Record<string, string | number>,
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  Object.entries(params ?? {}).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(await describe(response))
  return response.json()
}

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) throw new Error(await describe(response))
  return response.json()
}

async function describe(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join('; ')
  } catch {
    /* fall through to the status line */
  }
  return `${response.status} ${response.statusText}`
}

export interface AdvisoryInput {
  village_shrid?: string
  village_query?: string
  state: string
  savings: number
  business_category: string
  social_category: string
  annual_family_income?: number | null
  is_woman: boolean
  has_prior_experience: boolean
  radius_km: number
  moratorium_mode: 'serviced' | 'capitalized'
  language: Language
  members?: GroupMemberInput[]
  liability_split?: 'equal' | 'proportional'
}

export interface GroupMemberInput {
  name?: string | null
  social_category: string
  annual_family_income?: number | null
  contribution: number
  is_woman?: boolean
}

export interface FinanceInput {
  margin: number
  business_category: string
  units?: number
  revenue_factor?: number
}

/** The finance layer only. The feasibility estimators are not re-run, which is what makes this
 *  fast enough to sit behind a slider. */
export interface FinanceResult {
  scheme: { max_loan: string; scheme_name: string }
  right_sizing: {
    recommended_loan: string
    required_capital: string
    debt_need: string
    capital_shortfall: string
    recommended_min_dscr: string
    dscr_threshold: string
    binding: string
  }
  schedules: { recommended_loan: { instalment: string } | null }
}

export interface QuotedLineInput {
  description: string
  quantity?: number
  unit_rate?: number | null
  amount: number
}

export interface DocumentFields {
  // quotation
  vendor_name?: string | null
  vendor_gstin?: string | null
  quotation_date?: string | null
  lines?: QuotedLineInput[]
  total_amount?: number | null
  // certificates
  applicant_name?: string | null
  annual_family_income?: number | null
  issue_date?: string | null
  issuing_authority?: string | null
  certificate_number?: string | null
  state?: string | null
  category?: string | null
  sub_caste?: string | null
  attestation_present?: boolean
}

export type DocumentKind = 'quotation' | 'income_certificate' | 'caste_certificate' | 'unknown'

export interface DocumentReadResult {
  kind: DocumentKind
  scores: Record<string, number>
  proposed: DocumentFields
  confirmed: false
}

export interface DocumentCheck {
  id: string
  severity: 'ok' | 'warning' | 'problem'
  text_en: string
  text_hi: string
  figures: Record<string, string>
}

export interface DocumentMatchedLine {
  quoted: { description: string; quantity: string; unit_rate: string | null; amount: string }
  template_item: string | null
  template_amount: string | null
  excess_pct: string | null
  severity: 'ok' | 'warning' | 'problem'
}

export interface DocumentCheckResult {
  kind: DocumentKind
  severity: 'ok' | 'warning' | 'problem'
  ready: boolean
  checks: DocumentCheck[]
  matched_lines: DocumentMatchedLine[]
  figures: Record<string, string>
  sources: string[]
}

export const api = {
  /** `signal` lets the typeahead abandon a superseded request, so a slow early response cannot
   *  overwrite a fast later one. */
  searchVillages: (q: string, state?: string, signal?: AbortSignal) =>
    get<VillageMatch[]>('/villages/search', state ? { q, state } : { q }, signal),
  costTemplates: () => get<CostTemplate[]>('/cost-templates'),
  advisory: (input: AdvisoryInput) => post<AdvisoryResponse>('/advisory', input),
  financeStructure: (input: FinanceInput, signal?: AbortSignal) =>
    post<FinanceResult>('/finance/structure', input, signal),
  /** Text, never an image. OCR already ran on the device; this only proposes fields. */
  documentsRead: (text: string) => post<DocumentReadResult>('/documents/read', { text }),
  documentsCheck: (body: Record<string, unknown>) =>
    post<DocumentCheckResult>('/documents/check', body),
}
