export interface StatRow {
  label: string
  /** Undefined/empty rows are dropped by the component, so callers can build arrays inline. */
  value: string | undefined
}

interface Props {
  /** Null/false entries are skipped, so callers can build rows inline behind conditions. */
  rows: (StatRow | null | false | undefined)[]
  columns?: 2 | 3
}

/** A section's numbers stated as labelled facts, before any prose.
 *
 *  The report previously explained its figures in sentences, which buried the amounts a reader
 *  actually decides on. StatRows is the fix: the figures lead, each under its own label, in
 *  tabular numerals, and the one- or two-line narration underneath explains rather than states.
 *  UX4G ships no definition-list/stat-block pattern, so the grid is app-namespaced CSS over
 *  system type classes. */
export function StatRows({ rows, columns = 2 }: Props) {
  const visible = rows.filter((r): r is StatRow => Boolean(r && r.value))
  if (!visible.length) return null
  return (
    <dl className={`setubiz-stat-grid${columns === 3 ? ' setubiz-stat-grid-3' : ''}`}>
      {visible.map((r) => (
        <div className="setubiz-stat" key={r.label}>
          <dt className="ux4g-label-m-default ux4g-text-neutral-secondary">{r.label}</dt>
          <dd className="ux4g-title-s-strong setubiz-tabular setubiz-stat-value">{r.value}</dd>
        </div>
      ))}
    </dl>
  )
}
