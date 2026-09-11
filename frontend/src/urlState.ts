import type { AdvisoryInput } from './api'
import type { Language } from './types'

/** The report is a POST result and the backend persists nothing, so there is no report id to link
 *  to. The URL therefore carries the *inputs* and the report route re-runs the advisory on load.
 *
 *  That is cheap here because the app already re-runs the whole pipeline on every language switch
 *  by design — the prose is narrated server-side per language, and translating in the client is
 *  treated as a correctness bug. What it buys is a working back button, a link the reader can send
 *  to a bank officer or keep for later, and a language toggle that is just a URL change. */

const DEFAULTS = {
  state: 'Jharkhand',
  social_category: 'sc',
  radius_km: 10,
  /** Not collected from the reader. Exposing a moratorium choice would add a piece of financial
   *  jargon to the form for a decision almost no first-time borrower is equipped to make; the
   *  report shows the alternative side by side instead, which the backend already computes. */
  moratorium_mode: 'serviced' as const,
}

export function toSearchParams(input: AdvisoryInput): URLSearchParams {
  const p = new URLSearchParams()
  if (input.village_shrid) p.set('shrid', input.village_shrid)
  if (input.village_query) p.set('village', input.village_query)
  if (input.state !== DEFAULTS.state) p.set('state', input.state)
  p.set('savings', String(input.savings))
  p.set('category', input.business_category)
  if (input.social_category !== DEFAULTS.social_category) p.set('social', input.social_category)
  if (input.annual_family_income != null) p.set('income', String(input.annual_family_income))
  if (input.is_woman) p.set('woman', '1')
  // Default is true, so only the false case needs recording.
  if (!input.has_prior_experience) p.set('new', '1')
  if (input.radius_km !== DEFAULTS.radius_km) p.set('radius', String(input.radius_km))
  p.set('lang', input.language)
  return p
}

/** Returns null when the URL does not carry enough to run an advisory — the report route treats
 *  that as "go back to the form", not as an error to show the reader. */
export function fromSearchParams(p: URLSearchParams, language: Language): AdvisoryInput | null {
  const shrid = p.get('shrid') ?? undefined
  const village = p.get('village') ?? undefined
  const savings = Number(p.get('savings'))
  const category = p.get('category') ?? ''

  if (!shrid && !village) return null
  if (!Number.isFinite(savings) || savings <= 0) return null
  if (!category) return null

  const income = p.get('income')
  const radius = Number(p.get('radius'))

  return {
    village_shrid: shrid,
    village_query: village,
    state: p.get('state') ?? DEFAULTS.state,
    savings,
    business_category: category,
    social_category: p.get('social') ?? DEFAULTS.social_category,
    annual_family_income: income == null || income === '' ? null : Number(income),
    is_woman: p.get('woman') === '1',
    has_prior_experience: p.get('new') !== '1',
    radius_km: Number.isFinite(radius) && radius > 0 ? radius : DEFAULTS.radius_km,
    moratorium_mode: DEFAULTS.moratorium_mode,
    language,
  }
}

/** The URL is the source of truth for language once a report exists, so a shared link opens in the
 *  language it was shared in. */
export function languageFromParams(p: URLSearchParams): Language | null {
  const raw = p.get('lang')
  return raw === 'en' || raw === 'hi' ? raw : null
}
