import type { Strings } from '../../format'

/** UX4G Footer, dark variant.
 *
 *  Carries the links a Government of India service is required to publish, plus one thing this
 *  service specifically owes its reader: the disclaimer that a report is advice, not a sanction.
 *  That sentence sits above the link columns rather than in the legal strip, because someone who
 *  misreads this page as an approved loan has been actively harmed by the product. */
export function SiteFooter({ strings, buildDate }: { strings: Strings; buildDate: string }) {
  return (
    <footer className="ux4g-footer ux4g-footer-dark setubiz-no-print">
      <div className="ux4g-footer-wrapper">
        <p className="ux4g-body-m-strong setubiz-measure">{strings.disclaimer}</p>

        <div className="ux4g-divider-horizontal ux4g-mt-l ux4g-mb-l" />

        <div className="ux4g-f-links ux4g-w-100">
          <div className="ux4g-col">
            <p className="ux4g-label-l-strong ux4g-mb-m">{strings.footerAbout}</p>
            <ul className="ux4g-f-link-list">
              <li>
                <a className="ux4g-text-link-neutral-sm" href="https://socialjustice.gov.in/">
                  {strings.ministry}
                </a>
              </li>
              <li>
                <a className="ux4g-text-link-neutral-sm" href="https://nsfdc.nic.in/">
                  NSFDC
                </a>
              </li>
              <li>
                <a className="ux4g-text-link-neutral-sm" href="https://nbcfdc.gov.in/">
                  NBCFDC
                </a>
              </li>
              <li>
                <a className="ux4g-text-link-neutral-sm" href="https://nskfdc.nic.in/">
                  NSKFDC
                </a>
              </li>
            </ul>
          </div>

          <div className="ux4g-col">
            <p className="ux4g-label-l-strong ux4g-mb-m">{strings.footerLegal}</p>
            <ul className="ux4g-f-link-list">
              <li>
                <a className="ux4g-text-link-neutral-sm" href="#accessibility">
                  {strings.accessibilityStatement}
                </a>
              </li>
              <li>
                <a className="ux4g-text-link-neutral-sm" href="#privacy">
                  {strings.privacyPolicy}
                </a>
              </li>
              <li>
                <a className="ux4g-text-link-neutral-sm" href="#rti">
                  {strings.rti}
                </a>
              </li>
              <li>
                <a className="ux4g-text-link-neutral-sm" href="#terms">
                  {strings.termsOfUse}
                </a>
              </li>
            </ul>
          </div>

          <div className="ux4g-col">
            <p className="ux4g-label-l-strong ux4g-mb-m">{strings.footerHelp}</p>
            <ul className="ux4g-f-link-list">
              <li>
                <a className="ux4g-text-link-neutral-sm" href="tel:1800110001">
                  1800 11 0001
                </a>
              </li>
              <li>
                <span className="ux4g-body-s-default">
                  {strings.lastUpdated}: {buildDate}
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div className="ux4g-divider-horizontal ux4g-mt-l ux4g-mb-l" />

        <p className="ux4g-body-s-default">{strings.copyright}</p>
      </div>
    </footer>
  )
}
