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
    officialData: 'Built on official government data',
    officialDataNote:
      'Every village, market and scheme figure in this report comes from published Government of India sources, listed with links at the end. Nothing is simulated.',
    publishedBy: 'Published by',
    grounded: 'figures checked against the facts object',
    documents: 'Documents to carry',
    apply: 'Where to apply',
    contents: 'Contents',
    jumpTo: 'Jump to section',
    keyFigures: 'The answer',
    warningsHeading: 'Read this before you borrow',
    source: 'Source',
    narrator: 'narrator',
    addressableMarket: 'addressable market',
    existingEnterprises: 'Existing enterprises',
    priceSpread: 'Market price spread',
    theme: 'Appearance',
    themeSystem: 'System',
    themeLight: 'Light',
    themeDark: 'Dark',

    // Chrome. Short, literal, no welcome copy — every string here has to do work.
    govOfIndia: 'Government of India',
    ministry: 'Ministry of Social Justice and Empowerment',
    skipToMain: 'Skip to main content',
    textSize: 'Text size',
    textSmaller: 'Smaller text',
    textReset: 'Normal text',
    textLarger: 'Larger text',
    languageLabel: 'Language',
    home: 'Home',
    yourReport: 'Your report',
    newReport: 'Start again',
    notFoundTitle: 'This page does not exist',
    notFoundBody: 'The link may be old or mistyped. Start again from the beginning.',
    reportGoneTitle: 'This link is missing some details',
    reportGoneBody: 'We cannot rebuild the report from this link. Please answer the questions again.',
    loadingReport: 'Preparing your report…',
    loadFailed: 'We could not prepare your report',
    tryAgain: 'Try again',
    // Village matching. The matcher returns a score; the reader gets a word, not a percentage.
    bestMatch: 'Closest match',
    possibleMatch: 'Also possible',
    change: 'Change',
    searching: 'Looking…',
    noVillageTitle: 'No village found with that name',
    noVillageBody: 'Try a different spelling, or the name of the nearest larger village.',
    selected: 'Selected',
    required: 'Needed to continue',
    savingsTooLow: 'Enter how much of your own money you can put in, for example 50,000.',
    pickBusiness: 'Choose one business to continue.',
    pickVillage: 'Choose your village from the list to continue.',
    km: 'km',
    unitCost: 'This unit costs about',

    // The five steps. Each heading is the question itself, asked in the second person.
    stepOf: 'Step {n} of {total}',
    next: 'Next',
    backStep: 'Back',
    step1Label: 'Village',
    step1Title: 'Where is your village?',
    step1Help: 'Say it or type it. We will show you the closest matches to pick from.',
    step2Label: 'Distance',
    step2Title: 'How far can you sell?',
    step2Help: 'The distance you can reach to sell, by foot, cycle or shared vehicle.',
    step3Label: 'Business',
    step3Title: 'What do you want to start?',
    step3Help: 'Pick one. You can come back and try another later.',
    step4Label: 'Savings',
    step4Title: 'How much money do you have?',
    step4Help: 'Your own money that you can put into the business. Not a loan.',
    step5Label: 'About you',
    step5Title: 'A little about you',
    step5Help: 'This decides which scheme you qualify for.',

    // Report. The answer comes first and is one sentence; evidence is opened on demand.
    answerTitle: 'Your answer',
    answerLead: 'You should borrow',
    whyThis: 'Why this amount?',
    showDetail: 'Show details',
    hideDetail: 'Hide details',
    openAll: 'Open all sections',

    // Plain-language glosses. The report is read by people who have never seen these terms.
    dscrGloss: 'Can you still repay in a bad year?',
    bindingGloss: 'What limits your loan',
    provenanceGloss: 'Where this number comes from',
    marginGloss: 'Your own money in the business',
    moratoriumAlt: 'What if you pay the interest later instead?',

    // Footer. Mandatory government links.
    footerHelp: 'Help and contact',
    footerAbout: 'About this service',
    footerLegal: 'Legal',
    accessibilityStatement: 'Accessibility statement',
    privacyPolicy: 'Privacy policy',
    rti: 'Right to Information',
    termsOfUse: 'Terms of use',
    lastUpdated: 'Last updated',
    copyright: 'Content owned by the Ministry of Social Justice and Empowerment, Government of India.',
    disclaimer:
      'This is guidance, not a loan sanction. The lending bank or State Channelizing Agency makes the final decision.',

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
    officialData: 'सरकारी आधिकारिक आँकड़ों पर आधारित',
    officialDataNote:
      'इस रिपोर्ट के गाँव, बाज़ार एवं योजना संबंधी सभी आँकड़े भारत सरकार के प्रकाशित स्रोतों से लिए गए हैं, जिनकी सूची लिंक सहित अंत में दी गई है। कोई भी आँकड़ा काल्पनिक नहीं है।',
    publishedBy: 'प्रकाशक',
    synthetic: 'प्रदर्शन डेटा',
    syntheticNote:
      'यह रिपोर्ट कृत्रिम नमूना डेटा पर बनी है। सूत्र, योजना के नियम और दरें वास्तविक हैं; गाँव एवं बाज़ार के आँकड़े नहीं।',
    grounded: 'आँकड़े तथ्य-वस्तु से मिलाए गए',
    documents: 'साथ ले जाने वाले दस्तावेज़',
    apply: 'आवेदन कहाँ करें',
    contents: 'विषय-सूची',
    jumpTo: 'अनुभाग पर जाएँ',
    keyFigures: 'मुख्य आँकड़े',
    warningsHeading: 'ऋण लेने से पहले यह पढ़ें',
    source: 'स्रोत',
    narrator: 'वर्णनकर्ता',
    addressableMarket: 'कुल बाज़ार',
    existingEnterprises: 'मौजूदा इकाइयाँ',
    priceSpread: 'बाज़ार मूल्य सीमा',
    theme: 'रूप',
    themeSystem: 'सिस्टम',
    themeLight: 'उजला',
    themeDark: 'गहरा',

    govOfIndia: 'भारत सरकार',
    ministry: 'सामाजिक न्याय एवं अधिकारिता मंत्रालय',
    skipToMain: 'मुख्य सामग्री पर जाएँ',
    textSize: 'अक्षर का आकार',
    textSmaller: 'छोटे अक्षर',
    textReset: 'सामान्य अक्षर',
    textLarger: 'बड़े अक्षर',
    languageLabel: 'भाषा',
    home: 'मुख्य पृष्ठ',
    yourReport: 'आपकी रिपोर्ट',
    newReport: 'फिर से शुरू करें',
    notFoundTitle: 'यह पृष्ठ मौजूद नहीं है',
    notFoundBody: 'लिंक पुराना या गलत हो सकता है। कृपया शुरू से आरंभ करें।',
    reportGoneTitle: 'इस लिंक में कुछ जानकारी अधूरी है',
    reportGoneBody: 'इस लिंक से रिपोर्ट दोबारा नहीं बन सकती। कृपया प्रश्नों के उत्तर फिर से दें।',
    loadingReport: 'आपकी रिपोर्ट तैयार हो रही है…',
    loadFailed: 'हम आपकी रिपोर्ट तैयार नहीं कर सके',
    tryAgain: 'फिर से कोशिश करें',
    bestMatch: 'सबसे मिलता-जुलता',
    possibleMatch: 'यह भी हो सकता है',
    change: 'बदलें',
    searching: 'खोज रहे हैं…',
    noVillageTitle: 'इस नाम का कोई गाँव नहीं मिला',
    noVillageBody: 'दूसरी वर्तनी आज़माएँ, या पास के बड़े गाँव का नाम लिखें।',
    selected: 'चुना गया',
    required: 'आगे बढ़ने के लिए ज़रूरी',
    savingsTooLow: 'बताएँ कि आप अपना कितना पैसा लगा सकते हैं, जैसे 50,000।',
    pickBusiness: 'आगे बढ़ने के लिए एक व्यवसाय चुनें।',
    pickVillage: 'आगे बढ़ने के लिए सूची में से अपना गाँव चुनें।',
    km: 'कि.मी.',
    unitCost: 'इस इकाई की लागत लगभग',

    stepOf: 'चरण {n} / {total}',
    next: 'आगे',
    backStep: 'पीछे',
    step1Label: 'गाँव',
    step1Title: 'आपका गाँव कहाँ है?',
    step1Help: 'नाम बोलें या लिखें। हम मिलते-जुलते नाम दिखाएँगे, उनमें से चुन लें।',
    step2Label: 'दूरी',
    step2Title: 'आप कितनी दूर तक बेच सकते हैं?',
    step2Help: 'जितनी दूर आप पैदल, साइकिल या साझा वाहन से बेचने जा सकते हैं।',
    step3Label: 'व्यवसाय',
    step3Title: 'आप क्या शुरू करना चाहते हैं?',
    step3Help: 'एक चुनें। बाद में दूसरा भी देख सकते हैं।',
    step4Label: 'बचत',
    step4Title: 'आपके पास कितने पैसे हैं?',
    step4Help: 'आपका अपना पैसा जो आप व्यवसाय में लगा सकते हैं। ऋण नहीं।',
    step5Label: 'आपके बारे में',
    step5Title: 'आपके बारे में थोड़ा',
    step5Help: 'इससे तय होगा कि आप किस योजना के पात्र हैं।',

    answerTitle: 'आपका उत्तर',
    answerLead: 'आपको लेना चाहिए',
    whyThis: 'यही राशि क्यों?',
    showDetail: 'विवरण दिखाएँ',
    hideDetail: 'विवरण छिपाएँ',
    openAll: 'सभी अनुभाग खोलें',

    dscrGloss: 'खराब वर्ष में भी क्या आप चुका पाएँगे?',
    bindingGloss: 'आपका ऋण किससे सीमित है',
    provenanceGloss: 'यह आँकड़ा कहाँ से आया',
    marginGloss: 'व्यवसाय में आपका अपना पैसा',
    moratoriumAlt: 'यदि ब्याज बाद में चुकाएँ तो?',

    footerHelp: 'सहायता एवं संपर्क',
    footerAbout: 'इस सेवा के बारे में',
    footerLegal: 'कानूनी',
    accessibilityStatement: 'सुगम्यता विवरण',
    privacyPolicy: 'गोपनीयता नीति',
    rti: 'सूचना का अधिकार',
    termsOfUse: 'उपयोग की शर्तें',
    lastUpdated: 'अंतिम अद्यतन',
    copyright: 'सामग्री का स्वामित्व सामाजिक न्याय एवं अधिकारिता मंत्रालय, भारत सरकार के पास है।',
    disclaimer:
      'यह केवल सलाह है, ऋण स्वीकृति नहीं। अंतिम निर्णय ऋण देने वाला बैंक या राज्य चैनलाइज़िंग एजेंसी लेगी।',

    quadrant: {
      strength: 'ताकत',
      weakness: 'कमजोरी',
      opportunity: 'अवसर',
      threat: 'जोखिम',
    },
  },
}

export type Strings = (typeof T)['en']
