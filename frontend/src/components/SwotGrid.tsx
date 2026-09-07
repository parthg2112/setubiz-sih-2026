interface Props {
  quadrants: Record<string, string[]>
  labels: { strength: string; weakness: string; opportunity: string; threat: string }
}

const TONE: Record<string, string> = {
  strength: 'var(--status-good)',
  weakness: 'var(--status-warning)',
  opportunity: 'var(--series-1)',
  threat: 'var(--status-critical)',
}

const ICON: Record<string, string> = {
  strength: '+',
  weakness: '−',
  opportunity: '↗',
  threat: '!',
}

export function SwotGrid({ quadrants, labels }: Props) {
  const order = ['strength', 'weakness', 'opportunity', 'threat'] as const
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {order.map((key) => {
        const items = quadrants[key] ?? []
        if (!items.length) return null
        return (
          <section
            key={key}
            className="print-block rounded-lg border border-hairline bg-surface p-4"
          >
            <h4 className="flex items-center gap-2 text-sm font-semibold text-ink">
              <span
                aria-hidden
                className="grid size-5 place-items-center rounded text-[11px] font-bold text-white"
                style={{ background: TONE[key] }}
              >
                {ICON[key]}
              </span>
              {labels[key]}
            </h4>
            <ul className="mt-2 space-y-2">
              {items.map((text, i) => (
                <li key={i} className="text-sm leading-relaxed text-ink-2">
                  {text}
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
