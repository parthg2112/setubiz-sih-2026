/** Text size control for the UX4G Accessibility Bar.
 *
 *  Every UX4G font size resolves to a rem value (--ux4g-font-size-16 is 1rem), so scaling the root
 *  font size moves the entire type system proportionally — headings, body, labels and line heights
 *  together — without touching a single UX4G token. That is the whole reason this is one line of
 *  state rather than a stylesheet.
 *
 *  This matters more here than on a typical service: the reader is frequently older, frequently
 *  reading outdoors on a small phone, and the document is about their own money. */

export type TextScale = 1 | 1.15 | 1.3

const STORAGE_KEY = 'setubiz-text-scale'
const STEPS: TextScale[] = [1, 1.15, 1.3]

/** The browser default. Scaling multiplies this rather than assuming 16px, so a user who has
 *  already raised their browser's default font size keeps that increase and ours on top. */
const BASE_PX = 16

export function storedScale(): TextScale {
  try {
    const raw = Number(localStorage.getItem(STORAGE_KEY))
    if (STEPS.includes(raw as TextScale)) return raw as TextScale
  } catch {
    // Private browsing throws on read; the default is fine.
  }
  return 1
}

export function applyScale(scale: TextScale): void {
  // Only touch the root when scaled, so at 1x the browser's own default still governs.
  document.documentElement.style.fontSize = scale === 1 ? '' : `${BASE_PX * scale}px`
  try {
    localStorage.setItem(STORAGE_KEY, String(scale))
  } catch {
    // Failing to remember the choice is not a reason to refuse to apply it.
  }
}

export function stepScale(current: TextScale, direction: 'up' | 'down'): TextScale {
  const i = STEPS.indexOf(current)
  const next = direction === 'up' ? i + 1 : i - 1
  return STEPS[Math.min(STEPS.length - 1, Math.max(0, next))]
}

export const MIN_SCALE: TextScale = STEPS[0]
export const MAX_SCALE: TextScale = STEPS[STEPS.length - 1]
