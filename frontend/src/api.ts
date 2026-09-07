import type { AdvisoryResponse, CostTemplate, Language, VillageMatch } from './types'

const BASE = '/api/v1'

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  Object.entries(params ?? {}).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  const response = await fetch(url)
  if (!response.ok) throw new Error(await describe(response))
  return response.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
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
}

export const api = {
  searchVillages: (q: string, state?: string) =>
    get<VillageMatch[]>('/villages/search', state ? { q, state } : { q }),
  costTemplates: () => get<CostTemplate[]>('/cost-templates'),
  advisory: (input: AdvisoryInput) => post<AdvisoryResponse>('/advisory', input),
}
