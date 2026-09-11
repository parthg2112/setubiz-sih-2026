import type { Strings } from '../format'
import type { Facts, Language } from '../types'

/** The screen for an applicant this scheme cannot serve.
 *
 *  The backend returns `max_loan: 0`, no schedules, and a referral list when the project cost sits
 *  outside the NSFDC envelope or no loan size is serviceable. Run through the normal report that
 *  produced "You should borrow ₹0" under a green tick, and a worst-year DSCR of 999.00 — a page
 *  that reads as an approval for nothing. There is no loan here, so this shows no loan: what
 *  happened, and which schemes can actually help. */
export function OutOfScope({
  facts,
  language,
  strings,
}: {
  facts: Facts
  language: Language
  strings: Strings
}) {
  const referrals = new Set(facts.scheme.referrals ?? [])
  const schemes = facts.eligibility.comparison.filter((s) => referrals.has(s.id))
  const shown = schemes.length > 0 ? schemes : facts.eligibility.comparison

  return (
    <section className="ux4g-mt-l setubiz-print-block" aria-labelledby="out-of-scope">
      <div className="ux4g-card ux4g-card-outline ux4g-card-vertical">
        <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-l">
          <div>
            <h2 className="ux4g-heading-l-strong" id="out-of-scope">
              {strings.outOfScopeTitle}
            </h2>
            {facts.warnings.map((w) => (
              <p className="ux4g-body-l-default setubiz-measure ux4g-mt-s" key={w.id}>
                {language === 'hi' ? w.text_hi : w.text_en}
              </p>
            ))}
          </div>

          <div>
            <h3 className="ux4g-title-m-strong ux4g-mb-s">{strings.otherSchemes}</h3>
            <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
              {shown.map((s) => (
                <div className="ux4g-result-list ux4g-result-list-v2" key={s.id}>
                  <div className="ux4g-result-list-content">
                    <div className="ux4g-result-list-header">
                      <span className="ux4g-result-list-title">
                        {language === 'hi' && s.name_hi ? s.name_hi : s.name}
                      </span>
                    </div>
                    <p className="ux4g-body-m-default setubiz-measure">
                      <span className="ux4g-label-m-strong">{strings.whenToPrefer}: </span>
                      {s.when_to_prefer}
                    </p>
                    {s.portal && (
                      <a
                        className="ux4g-text-link-sm"
                        href={s.portal}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {strings.visitPortal}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
