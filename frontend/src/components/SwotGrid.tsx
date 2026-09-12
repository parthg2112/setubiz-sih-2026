interface Props {
  quadrants: Record<string, string[]>
  labels: { strength: string; weakness: string; opportunity: string; threat: string }
}

/** Colour never carries the meaning alone: each quadrant pairs its tint with a named icon and a
 *  written heading, so the grid reads identically in greyscale and on paper.
 *
 *  The rewrite from four card-of-paragraphs: a count strip answers "how bad is it overall" in one
 *  glance, and each finding is a compact row under a tinted quadrant header instead of a body-size
 *  paragraph. Surfaces are full tints, never side stripes. */
const QUADRANTS = [
  { key: 'strength', icon: 'trending_up', tone: 'strength' },
  { key: 'weakness', icon: 'trending_down', tone: 'weakness' },
  { key: 'opportunity', icon: 'lightbulb', tone: 'opportunity' },
  { key: 'threat', icon: 'report_problem', tone: 'threat' },
] as const

export function SwotGrid({ quadrants, labels }: Props) {
  const active = QUADRANTS.map((q) => ({ ...q, items: quadrants[q.key] ?? [] })).filter(
    (q) => q.items.length > 0,
  )
  if (!active.length) return null

  return (
    <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
      <div className="ux4g-d-flex ux4g-gap-x-s ux4g-flex-wrap" aria-hidden="true">
        {active.map((q) => (
          <span key={q.key} className={`setubiz-swot-chip setubiz-swot-chip-${q.tone}`}>
            <span className="ux4g-icon-outlined">{q.icon}</span>
            {labels[q.key]} × {q.items.length}
          </span>
        ))}
      </div>

      <div className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-2 ux4g-gap-m setubiz-print-block">
        {active.map((q) => (
          <section className={`setubiz-swot setubiz-swot-${q.tone}`} key={q.key} aria-label={labels[q.key]}>
            <h4 className="setubiz-swot-head">
              <span className="ux4g-icon-outlined" aria-hidden="true">
                {q.icon}
              </span>
              <span>{labels[q.key]}</span>
              <span className="setubiz-swot-count setubiz-tabular">{q.items.length}</span>
            </h4>
            <ul className="setubiz-swot-list">
              {q.items.map((text, i) => (
                <li className="setubiz-swot-item" key={i}>
                  <span className="ux4g-body-m-default">{text}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
