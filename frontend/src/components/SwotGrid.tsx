interface Props {
  quadrants: Record<string, string[]>
  labels: { strength: string; weakness: string; opportunity: string; threat: string }
}

/** Colour never carries the meaning alone: each quadrant pairs its tone with a named icon and a
 *  written heading, so the grid reads identically in greyscale and on paper. */
const QUADRANTS = [
  { key: 'strength', tag: 'ux4g-tag-tonal-success', icon: 'trending_up' },
  { key: 'weakness', tag: 'ux4g-tag-tonal-warning', icon: 'trending_down' },
  { key: 'opportunity', tag: 'ux4g-tag-tonal-info', icon: 'lightbulb' },
  { key: 'threat', tag: 'ux4g-tag-tonal-error', icon: 'report_problem' },
] as const

export function SwotGrid({ quadrants, labels }: Props) {
  return (
    <div className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-2 ux4g-gap-m">
      {QUADRANTS.map(({ key, tag, icon }) => {
        const items = quadrants[key] ?? []
        if (!items.length) return null
        return (
          <section
            className="ux4g-card ux4g-card-outline ux4g-card-vertical setubiz-print-block"
            key={key}
          >
            <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
              <h4 className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-s">
                <span className={`${tag} ux4g-tag-s ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs`}>
                  <span className="ux4g-icon-outlined" aria-hidden="true">
                    {icon}
                  </span>
                  {labels[key]}
                </span>
              </h4>
              <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
                {items.map((text, i) => (
                  <li className="ux4g-body-l-default setubiz-measure" key={i}>
                    {text}
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )
      })}
    </div>
  )
}
