/** Theme control and the shared chart palette.
 *
 *  UX4G switches themes with data-theme="light" | "dark" on <html> — components have no fallback
 *  theme, so the attribute is always written, never omitted. index.html stamps the same attribute
 *  before first paint so the page does not flash light before React mounts. */

export type ThemeChoice = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'setubiz-theme'

/** The three DSCR series, in severity order: base case, revenue -15%, revenue -30%.
 *  Defined in app.css as aliases onto UX4G primitive ramps; see the note there. */
export const SERIES = [
  'var(--setubiz-chart-1)',
  'var(--setubiz-chart-2)',
  'var(--setubiz-chart-3)',
] as const

export function storedTheme(): ThemeChoice {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === 'light' || raw === 'dark' || raw === 'system') return raw
  } catch {
    // Private browsing and blocked site data both throw here; the default is fine.
  }
  return 'system'
}

function prefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function applyTheme(choice: ThemeChoice): void {
  const dark = choice === 'dark' || (choice === 'system' && prefersDark())
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', dark ? '#171717' : '#fafafa')
  try {
    localStorage.setItem(STORAGE_KEY, choice)
  } catch {
    // Not being able to remember the choice is not a reason to refuse to apply it.
  }
}

/** Re-applies on OS change while the choice is `system`. Returns an unsubscribe. */
export function watchSystemTheme(getChoice: () => ThemeChoice): () => void {
  const query = window.matchMedia('(prefers-color-scheme: dark)')
  const onChange = () => {
    if (getChoice() === 'system') applyTheme('system')
  }
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}
