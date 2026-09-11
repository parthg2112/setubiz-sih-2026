import { inr, type Strings } from '../format'
import type { AltConfiguration, Language, SectionData } from '../types'

interface Props {
  data: SectionData
  language: Language
  strings: Strings
}

/** English takes a plural 's'; Hindi does not, so the Hindi branch never calls this. */
function units(count: number, label: string, language: Language): string {
  if (language !== 'en') return `${count} ${label}`
  return `${count} ${label}${count === 1 ? '' : 's'}`
}

/** The answer to "start smaller".
 *
 *  Shown directly under the headline figure, because when the recommended loan falls short of
 *  what the unit costs this is the reader's actual next question. Only sizes that both clear the
 *  appraisal norm and are fully funded appear as options; a size with a remaining gap is the same
 *  dead end at a different scale, so it is never offered as one.
 */
export function SizesThatWork({ data, language, strings }: Props) {
  const configurations = data.configurations ?? []
  const label = data.unit_label ?? ''
  const phased = data.phased

  return (
    <section
      className="ux4g-card ux4g-card-outline ux4g-card-vertical ux4g-mt-l setubiz-print-block"
      id="alternatives"
      data-section
      aria-labelledby="sizes-heading"
    >
      <div className="ux4g-card-header">
        <h2 className="ux4g-heading-m-strong ux4g-card-title" id="sizes-heading">
          {strings.sizesTitle}
        </h2>
      </div>

      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
        {configurations.length > 0 ? (
          <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
            {configurations.map((c) => (
              <SizeRow key={c.units} config={c} label={label} language={language} strings={strings} />
            ))}
          </ul>
        ) : (
          <NoSizeFits data={data} language={language} strings={strings} />
        )}

        {phased && (
          <div className="ux4g-alert ux4g-alert-info">
            <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
              trending_up
            </span>
            <div className="ux4g-alert-content">
              <p className="ux4g-alert-title">{strings.sizesPhased}</p>
              <p className="ux4g-alert-message setubiz-measure">
                {strings.sizesPhasedBody
                  .replace('{start}', units(phased.start_units, label, language))
                  .replace('{target}', units(phased.target_units, label, language))
                  .replace('{years}', String(phased.years_to_expand))}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function SizeRow({
  config,
  label,
  language,
  strings,
}: {
  config: AltConfiguration
  label: string
  language: Language
  strings: Strings
}) {
  return (
    <li className="ux4g-card ux4g-card-outline">
      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-wrap ux4g-ai-center ux4g-jc-between ux4g-gap-m">
        <div>
          <p className="ux4g-title-s-strong">{units(config.units, label, language)}</p>
          <p className="ux4g-body-m-default ux4g-text-neutral-secondary setubiz-tabular">
            {strings.sizesCost} {inr(config.project_cost)}
          </p>
        </div>

        <div>
          <p className="ux4g-body-s-default ux4g-text-neutral-tertiary">{strings.sizesLoan}</p>
          <p className="ux4g-title-s-strong setubiz-tabular">
            {config.self_financed ? strings.sizesNoLoan : inr(config.loan)}
          </p>
        </div>

        {!config.self_financed && (
          <div>
            <p className="ux4g-body-s-default ux4g-text-neutral-tertiary">
              {strings.sizesPerQuarter}
            </p>
            <p className="ux4g-title-s-strong setubiz-tabular">{inr(config.instalment)}</p>
          </div>
        )}

        {/* Icon and word together: the tone is never the only signal. */}
        <span
          className={
            config.comfort === 'comfortable'
              ? 'ux4g-tag-tonal-success ux4g-tag-s ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs'
              : 'ux4g-tag-tonal-warning ux4g-tag-s ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs'
          }
        >
          <span className="ux4g-icon-outlined" aria-hidden="true">
            {config.comfort === 'comfortable' ? 'check_circle' : 'error'}
          </span>
          {config.comfort === 'comfortable' ? strings.sizesComfortable : strings.sizesTight}
        </span>
      </div>
    </li>
  )
}

function NoSizeFits({ data, language, strings }: Props) {
  const label = data.unit_label ?? ''
  return (
    <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
      <div className="ux4g-alert ux4g-alert-warning">
        <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
          info
        </span>
        <div className="ux4g-alert-content">
          <p className="ux4g-alert-title">{strings.sizesNone}</p>
          <p className="ux4g-alert-message setubiz-measure">{strings.sizesBiggerCheaper}</p>
        </div>
      </div>

      {data.closest_units != null && data.additional_margin_needed != null && (
        <dl className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-2 ux4g-gap-m">
          <div>
            <dt className="ux4g-body-s-default ux4g-text-neutral-tertiary">
              {strings.sizesGapAt}
            </dt>
            <dd className="ux4g-title-m-strong">
              {units(data.closest_units, label, language)}
            </dd>
          </div>
          <div>
            <dt className="ux4g-body-s-default ux4g-text-neutral-tertiary">
              {strings.sizesNeedMore}
            </dt>
            <dd className="ux4g-title-m-strong ux4g-text-primary setubiz-tabular">
              {inr(data.additional_margin_needed)}
            </dd>
          </div>
        </dl>
      )}
    </div>
  )
}
