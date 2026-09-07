/** Display formatting. Mirrors setubiz.money so the screen and the report never disagree. */

export function inr(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const n = Math.round(Number(value))
  if (!Number.isFinite(n)) return '—'
  const negative = n < 0
  const digits = String(Math.abs(n))
  let grouped = digits
  if (digits.length > 3) {
    const tail = digits.slice(-3)
    let head = digits.slice(0, -3)
    const parts: string[] = []
    while (head.length > 2) {
      parts.unshift(head.slice(-2))
      head = head.slice(0, -2)
    }
    if (head) parts.unshift(head)
    grouped = [...parts, tail].join(',')
  }
  return `${negative ? '-' : ''}₹${grouped}`
}

export function lakh(value: string | number): string {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return inr(n)
}

export function ratio(value: string | number): string {
  return Number(value).toFixed(2)
}

export function pct(value: string | number, digits = 0): string {
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export const BINDING_LABEL: Record<string, { en: string; hi: string }> = {
  dscr: { en: 'limited by repayment capacity', hi: 'चुकौती क्षमता से सीमित' },
  stress: { en: 'limited by what survives a bad year', hi: 'खराब वर्ष झेलने की क्षमता से सीमित' },
  scheme_cap: { en: 'limited by the scheme ceiling', hi: 'योजना की अधिकतम सीमा से सीमित' },
  capital_need: { en: 'limited by what the unit costs', hi: 'इकाई की वास्तविक लागत से सीमित' },
  not_viable: { en: 'no loan size is serviceable', hi: 'कोई भी ऋण राशि चुकाने योग्य नहीं' },
}

/** UI strings. Deliberately not `as const` — the two language tables must share one widened
 *  shape, or every consumer sees a union of literal types. */
export const T = {
  en: {
    appName: 'SetuBiz',
    tagline: 'Borrow what you can repay, not what the formula allows.',
    village: 'Your village',
    villagePlaceholder: 'Say or type the village name',
    confirm: 'Which one?',
    savings: 'Your own savings (margin money)',
    business: 'What do you want to start?',
    social: 'Social category',
    income: 'Annual family income (optional)',
    woman: 'Woman entrepreneur',
    experienced: 'I have worked in this trade before',
    radius: 'How far can you sell?',
    submit: 'Get my advice',
    working: 'Working…',
    back: 'Start over',
    print: 'Print / save as PDF',
    maxLoan: 'Loan you CAN get',
    recommended: 'Loan you SHOULD take',
    difference: 'Difference',
    provenance: 'Where did that number come from?',
    close: 'Close',
    schedule: 'Quarterly repayment schedule',
    showSchedule: 'Show all instalments',
    hideSchedule: 'Hide instalments',
    tableView: 'Table view',
    worstYear: 'worst-year DSCR',
    listening: 'Listening…',
    speak: 'Speak',
    micUnsupported: 'Voice input is not available in this browser. Please type instead.',
    synthetic: 'Demonstration data',
    syntheticNote:
      'This report is built on synthetic sample data. The formulae, scheme rules and rates are real; the village and market rows are not.',
    grounded: 'figures checked against the facts object',
    documents: 'Documents to carry',
    apply: 'Where to apply',
    quadrant: {
      strength: 'Strengths',
      weakness: 'Weaknesses',
      opportunity: 'Opportunities',
      threat: 'Threats',
    },
  },
  hi: {
    appName: 'सेतुबिज़',
    tagline: 'उतना लें जितना चुका सकें, उतना नहीं जितना सूत्र देता है।',
    village: 'आपका गाँव',
    villagePlaceholder: 'गाँव का नाम बोलें या लिखें',
    confirm: 'कौन सा?',
    savings: 'आपकी अपनी बचत (मार्जिन राशि)',
    business: 'आप क्या शुरू करना चाहते हैं?',
    social: 'सामाजिक श्रेणी',
    income: 'वार्षिक पारिवारिक आय (वैकल्पिक)',
    woman: 'महिला उद्यमी',
    experienced: 'मुझे इस काम का अनुभव है',
    radius: 'आप कितनी दूर तक बेच सकते हैं?',
    submit: 'मेरी सलाह दिखाएँ',
    working: 'गणना हो रही है…',
    back: 'फिर से शुरू करें',
    print: 'प्रिंट / पीडीएफ',
    maxLoan: 'जितना ऋण मिल सकता है',
    recommended: 'जितना ऋण लेना चाहिए',
    difference: 'अंतर',
    provenance: 'यह आँकड़ा कहाँ से आया?',
    close: 'बंद करें',
    schedule: 'तिमाही चुकौती अनुसूची',
    showSchedule: 'सभी किस्तें दिखाएँ',
    hideSchedule: 'किस्तें छिपाएँ',
    tableView: 'तालिका',
    worstYear: 'सबसे कमजोर वर्ष का डीएससीआर',
    listening: 'सुन रहे हैं…',
    speak: 'बोलें',
    micUnsupported: 'इस ब्राउज़र में आवाज़ उपलब्ध नहीं है। कृपया लिखें।',
    synthetic: 'प्रदर्शन डेटा',
    syntheticNote:
      'यह रिपोर्ट कृत्रिम नमूना डेटा पर बनी है। सूत्र, योजना के नियम और दरें वास्तविक हैं; गाँव एवं बाज़ार के आँकड़े नहीं।',
    grounded: 'आँकड़े तथ्य-वस्तु से मिलाए गए',
    documents: 'साथ ले जाने वाले दस्तावेज़',
    apply: 'आवेदन कहाँ करें',
    quadrant: {
      strength: 'ताकत',
      weakness: 'कमजोरी',
      opportunity: 'अवसर',
      threat: 'जोखिम',
    },
  },
}

export type Strings = (typeof T)['en']
