import type { Strings } from '../../format'
import type { ThemeChoice } from '../../theme'

/** UX4G Navbar: identity on the left, appearance control on the right.
 *
 *  The appearance control is a labelled native select (`ux4g-form-select`, the system's
 *  cross-browser styled native element) rather than the previous three glyph-only buttons. A
 *  reader who has never used a theme switcher can read "Appearance: Light" and understand it;
 *  `◐ ☀ ☾` with the accessible name hidden in a `title` gave them nothing. */
export function SiteHeader({
  strings,
  theme,
  onTheme,
}: {
  strings: Strings
  theme: ThemeChoice
  onTheme: (next: ThemeChoice) => void
}) {
  return (
    <nav className="ux4g-navbar setubiz-no-print" aria-label={strings.appName}>
      <div className="ux4g-container">
        <div className="ux4g-navbar-wrap">
          <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-s">
            <div className="ux4g-d-flex ux4g-flex-column">
              <span className="ux4g-title-s-strong">{strings.appName}</span>
              <span className="ux4g-body-xs-default ux4g-text-neutral-secondary">
                {strings.ministry}
              </span>
            </div>
          </div>

          <div className="ux4g-navbar-right ux4g-d-flex ux4g-ai-center ux4g-gap-x-s">
            <label className="ux4g-label-m-default ux4g-d-none ux4g-md-d-block" htmlFor="appearance">
              {strings.theme}
            </label>
            <select
              id="appearance"
              className="ux4g-form-select ux4g-form-select-lg"
              value={theme}
              aria-label={strings.theme}
              onChange={(e) => onTheme(e.target.value as ThemeChoice)}
            >
              <option value="system">{strings.themeSystem}</option>
              <option value="light">{strings.themeLight}</option>
              <option value="dark">{strings.themeDark}</option>
            </select>
          </div>
        </div>
      </div>
    </nav>
  )
}
