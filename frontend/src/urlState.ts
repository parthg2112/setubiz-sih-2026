import type { AdvisoryInput, GroupMemberInput } from './api'
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
  // Group members ride in the URL like everything else, so a group report is as shareable as an
  // individual one. `category:income:contribution:name`, one `m` per member.
  for (const m of input.members ?? []) {
    p.append(
      'm',
      [m.social_category, m.annual_family_income ?? '', m.contribution, m.name ?? ''].join(':'),
    )
  }
  if (input.liability_split && input.liability_split !== 'equal') {
    p.set('split', input.liability_split)
  }
  return p
}

function parseMember(raw: string): GroupMemberInput | null {
  const [social_category, income, contribution, ...name] = raw.split(':')
  const amount = Number(contribution)
  if (!social_category || !Number.isFinite(amount) || amount <= 0) return null
  return {
    social_category,
    annual_family_income: income ? Number(income) : null,
    contribution: amount,
    name: name.join(':') || null,
  }
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
    members: p.getAll('m').map(parseMember).filter((m): m is GroupMemberInput => m !== null),
    liability_split: p.get('split') === 'proportional' ? 'proportional' : 'equal',
  }
}

/** The URL is the source of truth for language once a report exists, so a shared link opens in the
 *  language it was shared in. */
export function languageFromParams(p: URLSearchParams): Language | null {
  const raw = p.get('lang')
  return raw === 'en' || raw === 'hi' ? raw : null
}
