import type { Strings } from '../../format'
import { MAX_SCALE, MIN_SCALE, stepScale, type TextScale } from '../../textScale'
import type { Language } from '../../types'

/** UX4G Accessibility Bar.
 *
 *  Carries the skip link (which the previous build lacked entirely), the text size control, and
 *  the language switch. Markup follows the canonical Accessibility Bar contract; the two non
 *  `ux4g-` classes in the Storybook example (`india-flag`, `acc-top-divider`) are documentation
 *  shell and are deliberately not copied — `ux4g-divider-vertical` is the system's own separator. */
export function TopBar({
  strings,
  language,
  onLanguage,
  scale,
  onScale,
  busy,
}: {
  strings: Strings
  language: Language
  onLanguage: (next: Language) => void
  scale: TextScale
  onScale: (next: TextScale) => void
  busy: boolean
}) {
  return (
    <header className="ux4g-topbar setubiz-no-print" role="banner">
      <div className="ux4g-container">
        <div className="ux4g-topbar__wrap ux4g-d-flex ux4g-jc-between ux4g-ai-center">
          <a
            className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs"
            href="https://www.india.gov.in/"
            target="_blank"
            rel="noopener"
          >
            <span className="ux4g-label-m-default">{strings.govOfIndia}</span>
            <sup className="ux4g-icon-outlined" aria-hidden="true">
              open_in_new
            </sup>
          </a>

          <nav
            aria-label={strings.textSize}
            className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-s"
          >
            {/* First thing a keyboard user reaches on the page. */}
            <a className="ux4g-label-m-default ux4g-topbar__skip" href="#main-content">
              {strings.skipToMain}
            </a>

            <span className="ux4g-divider-vertical ux4g-d-none ux4g-md-d-flex" />

            <div
              aria-label={strings.textSize}
              className="ux4g-topbar__group ux4g-d-flex ux4g-ai-center"
              role="group"
            >
              <button
                aria-label={strings.textSmaller}
                className="ux4g-topbar__iconbtn ux4g-d-flex ux4g-jc-center ux4g-ai-center"
                type="button"
                disabled={scale === MIN_SCALE}
                onClick={() => onScale(stepScale(scale, 'down'))}
              >
                <span className="ux4g-icon-outlined ux4g-top-bar-icon" aria-hidden="true">
                  text_decrease
                </span>
              </button>
              <button
                aria-label={strings.textReset}
                className="ux4g-topbar__iconbtn ux4g-d-flex ux4g-jc-center ux4g-ai-center"
                type="button"
                onClick={() => onScale(MIN_SCALE)}
              >
                <span className="ux4g-icon-outlined ux4g-top-bar-icon" aria-hidden="true">
                  font_download
                </span>
              </button>
              <button
                aria-label={strings.textLarger}
                className="ux4g-topbar__iconbtn ux4g-d-flex ux4g-jc-center ux4g-ai-center"
                type="button"
                disabled={scale === MAX_SCALE}
                onClick={() => onScale(stepScale(scale, 'up'))}
              >
                <span className="ux4g-icon-outlined ux4g-top-bar-icon" aria-hidden="true">
                  text_increase
                </span>
              </button>
            </div>

            <span className="ux4g-divider-vertical" />

            {/* Two languages only, so a pair of buttons beats a dropdown: the choice is visible
                without opening anything, and each option is its own 44px target. */}
            <div
              aria-label={strings.languageLabel}
              className="ux4g-topbar__group ux4g-d-flex ux4g-ai-center"
              role="group"
            >
              <button
                className="ux4g-topbar__selectbtn ux4g-d-inline-flex ux4g-ai-center ux4g-gap-x-xs"
                type="button"
                aria-pressed={language === 'en'}
                disabled={busy}
                onClick={() => onLanguage('en')}
              >
                <span className="ux4g-icon-outlined ux4g-top-bar-icon" aria-hidden="true">
                  language
                </span>
                <span className="ux4g-label-m-default">English</span>
              </button>
              <button
                className="ux4g-topbar__selectbtn ux4g-d-inline-flex ux4g-ai-center"
                type="button"
                aria-pressed={language === 'hi'}
                disabled={busy}
                onClick={() => onLanguage('hi')}
              >
                <span className="ux4g-label-m-default">हिन्दी</span>
              </button>
            </div>
          </nav>
        </div>
      </div>
    </header>
  )
}
