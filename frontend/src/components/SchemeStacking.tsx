import { inr, type Strings } from '../format'
import type { SchemeCombination, SectionData } from '../types'

interface Props {
  data: SectionData
  strings: Strings
}

/** Which schemes may be held together.
 *
 *  Confirmed and unconfirmed combinations are rendered in visibly different groups, with
 *  different tones and different headings. Collapsing them into one list is how "confirm this at
 *  the district office" becomes "you qualify for both" in a reader's memory, and that reader then
 *  builds a project cost around assistance that never arrives.
 */
export function SchemeStacking({ data, strings }: Props) {
  const combinable = data.combinable ?? []
  const needsCheck = data.needs_verification ?? []
  const exclusive = data.mutually_exclusive ?? []

  if (!combinable.length && !needsCheck.length && !exclusive.length) return null

  return (
    <section
      className="ux4g-card ux4g-card-outline ux4g-card-vertical ux4g-mt-l setubiz-print-block"
      id="stacking"
      data-section
      aria-labelledby="stacking-heading"
    >
      <div className="ux4g-card-header">
        <h2 className="ux4g-heading-m-strong ux4g-card-title" id="stacking-heading">
          {strings.stackTitle}
        </h2>
      </div>

      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-l">
        {combinable.length > 0 && (
          <Group
            title={strings.stackCombinable}
            tone="success"
            icon="check_circle"
            combinations={combinable}
            strings={strings}
          />
        )}

        {needsCheck.length > 0 && (
          <Group
            title={strings.stackNeedsCheck}
            body={strings.stackNeedsCheckBody}
            tone="warning"
            icon="help"
            combinations={needsCheck}
            strings={strings}
          />
        )}

        {exclusive.length > 0 && (
          <Group
            title={strings.stackExclusive}
            tone="error"
            icon="block"
            combinations={exclusive}
            strings={strings}
          />
        )}
      </div>
    </section>
  )
}

function Group({
  title,
  body,
  tone,
  icon,
  combinations,
  strings,
}: {
  title: string
  body?: string
  tone: 'success' | 'warning' | 'error'
  icon: string
  combinations: SchemeCombination[]
  strings: Strings
}) {
  return (
    <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
      {/* Icon plus word, never tone alone. */}
      <h3 className="ux4g-title-s-strong ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs">
        <span className={`ux4g-icon-outlined ux4g-text-${tone}`} aria-hidden="true">
          {icon}
        </span>
        {title}
      </h3>

      {body && (
        <p className="ux4g-body-m-default ux4g-text-neutral-secondary setubiz-measure">{body}</p>
      )}

      <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
        {combinations.map((c) => (
          <li className="ux4g-card ux4g-card-outline" key={c.schemes.join('+')}>
            <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
              <p className="ux4g-label-l-strong">{c.names.join(' + ')}</p>
              <p className="ux4g-body-l-default setubiz-measure">{c.reason}</p>

              {c.sequencing && (
                <p className="ux4g-body-s-default ux4g-text-neutral-secondary">
                  {strings.stackSequencing}: {c.sequencing}
                </p>
              )}
              {c.combined_cap && (
                <p className="ux4g-body-s-default ux4g-text-neutral-secondary setubiz-tabular">
                  {strings.stackCap}: {inr(c.combined_cap)}
                </p>
              )}
              {c.source && (
                <a className="ux4g-text-link-sm" href={c.source} target="_blank" rel="noreferrer">
                  {strings.stackSource}
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
