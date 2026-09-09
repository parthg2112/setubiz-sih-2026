/** Theme control and the shared chart palette.
 *
 *  Dark mode is a single `.dark` class on <html>, written here for both an explicit choice and a
 *  system preference. index.html stamps the same class before first paint. */

export type ThemeChoice = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'setubiz-theme'

/** The three DSCR series, in severity order: base case, revenue -15%, revenue -30%.
 *  Validated all-pairs against both card surfaces; see index.css. */
export const SERIES = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)'] as const

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
  document.documentElement.classList.toggle('dark', dark)
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', dark ? '#000000' : '#ffffff')
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
