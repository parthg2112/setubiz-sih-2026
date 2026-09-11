import { Link } from 'react-router-dom'
import type { Strings } from '../format'

export function NotFound({ strings }: { strings: Strings }) {
  return (
    <div className="ux4g-container ux4g-py-2xl">
      <div className="ux4g-empty-state">
        <span className="ux4g-icon-outlined ux4g-empty-state-icon ux4g-text-primary" aria-hidden="true">
          error_outline
        </span>
        <div className="ux4g-empty-state-content">
          <h1 className="ux4g-title-l-strong">{strings.notFoundTitle}</h1>
          <p className="ux4g-body-l-default setubiz-measure">{strings.notFoundBody}</p>
        </div>
        <Link className="ux4g-btn ux4g-btn-tonal-primary ux4g-btn-md" to="/">
          {strings.home}
        </Link>
      </div>
    </div>
  )
}
