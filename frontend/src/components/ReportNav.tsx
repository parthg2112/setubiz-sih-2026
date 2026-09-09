import { useEffect, useState } from 'react'
import { BINDING_LABEL, inr, ratio, type Strings } from '../format'
import type { Facts, Language } from '../types'

export interface NavItem {
  id: string
  label: string
}

interface Props {
  items: NavItem[]
  facts: Facts
  language: Language
  strings: Strings
  provenanceCount: number
  onProvenance: () => void
  onRestart: () => void
}

/** Tracks which section owns the viewport. Plain IntersectionObserver: a scroll-spy is not worth
 *  a dependency, and the report is a fixed handful of sections. */
function useActiveSection(ids: string[]): string | null {
  const [active, setActive] = useState<string | null>(ids[0] ?? null)

  useEffect(() => {
    const seen = new Map<string, number>()
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          seen.set(entry.target.id, entry.isIntersecting ? entry.intersectionRatio : 0)
        }
        // The topmost visible section wins, so a tall section does not steal focus from the
        // short one the reader has just scrolled onto.
        const visible = ids.filter((id) => (seen.get(id) ?? 0) > 0)
        if (visible.length > 0) setActive(visible[0])
      },
      { rootMargin: '-88px 0px -55% 0px', threshold: [0, 0.01] },
    )
    for (const id of ids) {
      const node = document.getElementById(id)
      if (node) observer.observe(node)
    }
    return () => observer.disconnect()
  }, [ids.join('|')]) // eslint-disable-line react-hooks/exhaustive-deps

  return active
}

export function ReportNav({
  items,
  facts,
  language,
  strings,
  provenanceCount,
  onProvenance,
  onRestart,
}: Props) {
  const active = useActiveSection(items.map((i) => i.id))
  const rs = facts.right_sizing
  const binding = BINDING_LABEL[rs.binding]

  return (
    <>
      {/* Desktop rail. */}
      <aside className="no-print hidden lg:block">
        <nav
          aria-label={strings.contents}
          className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto pb-8"
        >
          <p className="px-3 text-[11px] font-semibold uppercase tracking-wider text-subtle-foreground">
            {strings.contents}
          </p>
          <ul className="mt-2 space-y-0.5">
            {items.map((item) => {
              const on = item.id === active
              return (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    aria-current={on ? 'true' : undefined}
                    className={`block rounded-xs px-3 py-1.5 text-sm leading-snug transition-colors ${
                      on
                        ? 'bg-accent font-medium text-accent-foreground'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`}
                  >
                    {item.label}
                  </a>
                </li>
              )
            })}
          </ul>

          <div className="mt-6 rounded-lg border border-border bg-card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-subtle-foreground">
              {strings.keyFigures}
            </p>
            <p className="tabular mt-1.5 text-2xl font-semibold tracking-tight text-foreground">
              {inr(rs.recommended_loan)}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">{strings.recommended}</p>
            <dl className="mt-3 space-y-1.5 border-t border-border pt-3 text-xs">
              <div className="flex items-baseline justify-between gap-2">
                <dt className="text-muted-foreground">{strings.worstYear}</dt>
                <dd className="tabular font-medium text-foreground">
                  {ratio(rs.recommended_min_dscr)}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-2">
                <dt className="text-muted-foreground">{strings.maxLoan}</dt>
                <dd className="tabular font-medium text-foreground">{inr(rs.max_loan)}</dd>
              </div>
            </dl>
            {binding && (
              <p className="mt-3 text-xs leading-snug text-subtle-foreground">
                {binding[language]}
              </p>
            )}
          </div>

          <div className="mt-4 space-y-1.5">
            <RailButton onClick={onProvenance}>
              {strings.provenance} ({provenanceCount})
            </RailButton>
            <RailButton onClick={() => window.print()}>{strings.print}</RailButton>
            <RailButton onClick={onRestart}>{strings.back}</RailButton>
          </div>
        </nav>
      </aside>

      {/* Below lg the rail becomes a scrolling chip row, so mobile keeps the same navigation. */}
      <nav
        aria-label={strings.jumpTo}
        className="no-print -mx-4 mb-5 overflow-x-auto px-4 lg:hidden"
      >
        <ul className="flex w-max gap-1.5">
          {items.map((item) => (
            <li key={item.id}>
              <a
                href={`#${item.id}`}
                className="block whitespace-nowrap rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground"
              >
                {item.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </>
  )
}

function RailButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-xs border border-border px-3 py-2 text-left text-xs font-medium text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
    >
      {children}
    </button>
  )
}
