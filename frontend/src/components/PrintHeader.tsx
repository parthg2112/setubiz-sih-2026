import { inr, SOCIAL_LABELS, type Strings } from '../format'
import type { Facts } from '../types'
import type { AdvisoryInput } from '../api'

interface Props {
  facts: Facts
  input: AdvisoryInput | null
  language: 'en' | 'hi'
  strings: Strings
}

/** The paper identity of the report.
 *
 *  On screen this block is noise: the wizard knows who is asking. On paper the sheet travels
 *  without its context, to a bank counter where nobody knows which applicant, which business or
 *  which savings figure produced these numbers. So the printed document opens with the applicant's
 *  own inputs, restated from the URL the report was generated from, before any analysis. The
 *  block is always rendered and only ever visible in print. */
export function PrintHeader({ facts, input, language, strings }: Props) {
  const hi = language === 'hi'
  const social = input ? SOCIAL_LABELS[input.social_category] : undefined
  const rows: { label: string; value: string }[] = [
    {
      label: strings.village,
      value: `${hi && facts.village.name_hi ? facts.village.name_hi : facts.village.name}, ${facts.village.block}, ${facts.village.district}, ${facts.village.state}`,
    },
    {
      label: strings.business,
      value: `${hi && facts.template.name_hi ? facts.template.name_hi : facts.template.name}`,
    },
    { label: strings.savings, value: inr(facts.scheme.margin) },
    {
      label: strings.income,
      value:
        input?.annual_family_income != null
          ? inr(input.annual_family_income)
          : hi
            ? 'जानकारी नहीं दी गई'
            : 'not provided',
    },
    { label: strings.social, value: social ? (hi ? social.hi : social.en) : input?.social_category ?? '' },
    { label: strings.woman, value: input?.is_woman ? (hi ? 'हाँ' : 'yes') : hi ? 'नहीं' : 'no' },
    {
      label: strings.experienced,
      value: input?.has_prior_experience ? (hi ? 'हाँ' : 'yes') : hi ? 'नहीं' : 'no',
    },
    { label: strings.radius, value: `${input?.radius_km ?? 10} ${strings.km}` },
  ]

  return (
    <div className="setubiz-print-only setubiz-print-head" aria-hidden="true">
      <div className="ux4g-d-flex ux4g-jc-between ux4g-gap-x-m">
        <div>
          <p className="ux4g-heading-s-strong setubiz-m-0">{strings.appName}</p>
          <p className="ux4g-body-s-default setubiz-m-0">
            {strings.govOfIndia} · {strings.ministry}
          </p>
        </div>
        <p className="ux4g-body-s-default setubiz-tabular setubiz-m-0">
          {strings.printGenerated}: {new Date(facts.generated_at).toLocaleDateString(hi ? 'hi-IN' : 'en-IN')}
        </p>
      </div>
      <p className="ux4g-label-l-strong setubiz-print-head-title">{strings.printPreparedFor}</p>
      <table className="ux4g-table setubiz-print-inputs">
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <th scope="row">{r.label}</th>
              <td className="setubiz-tabular">{r.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
