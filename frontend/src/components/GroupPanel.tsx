import { inr, type Strings } from '../format'
import type { SectionData } from '../types'

interface Props {
  data: SectionData
  body: string
  strings: Strings
}

/** The group, member by member.
 *
 *  Anyone who does not qualify is named in their own row. A group-level verdict that absorbed a
 *  failing member would send the whole group to the counter to find out, which is the outcome
 *  this mode exists to prevent.
 */
export function GroupPanel({ data, body, strings }: Props) {
  const members = data.members ?? []
  if (!members.length) return null

  return (
    <section
      className="ux4g-card ux4g-card-outline ux4g-card-vertical ux4g-mt-l setubiz-print-block"
      id="group"
      data-section
      aria-labelledby="group-heading"
    >
      <div className="ux4g-card-header">
        <h2 className="ux4g-heading-m-strong ux4g-card-title" id="group-heading">
          {strings.groupTitle}
        </h2>
        <p className="ux4g-body-l-default ux4g-card-sub-title setubiz-measure">{body}</p>
      </div>

      <div className="ux4g-card-body">
        <div className="ux4g-table-responsive">
          <table className="ux4g-table ux4g-table-m ux4g-table-zebra-rows ux4g-table-rounded">
            <thead>
              <tr>
                <th scope="col">
                  <span className="ux4g-table-th-content">{strings.memberLabel}</span>
                </th>
                <th scope="col">
                  <span className="ux4g-table-th-content">{strings.social}</span>
                </th>
                <th scope="col">
                  <span className="ux4g-table-th-content">{strings.groupContribution}</span>
                </th>
                <th scope="col">
                  <span className="ux4g-table-th-content">{strings.groupShare}</span>
                </th>
                <th scope="col">
                  <span className="ux4g-table-th-content">{strings.apply}</span>
                </th>
              </tr>
            </thead>
            <tbody className="setubiz-tabular">
              {members.map((m) => (
                <tr key={m.index}>
                  <th scope="row">
                    {m.name || `${strings.memberLabel} ${m.index}`}
                    {/* Icon and word, never tone alone. */}
                    <span
                      className={`${
                        m.qualifies ? 'ux4g-tag-tonal-success' : 'ux4g-tag-tonal-error'
                      } ux4g-tag-s ux4g-ml-xs`}
                    >
                      <span className="ux4g-icon-outlined" aria-hidden="true">
                        {m.qualifies ? 'check_circle' : 'cancel'}
                      </span>
                      {m.qualifies ? strings.groupQualify : strings.groupNotQualify}
                    </span>
                  </th>
                  <td>{m.social_category}</td>
                  <td>{inr(m.contribution)}</td>
                  <td>{m.liability === '0' ? '-' : inr(m.liability)}</td>
                  <td>{m.corporation ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
