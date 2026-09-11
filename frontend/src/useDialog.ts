import { useEffect, type RefObject } from 'react'

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

/** Modal dialog behaviour: focus trap, Escape to close, focus restored to the opener, and the
 *  page behind locked from scrolling.
 *
 *  The previous provenance panel declared `role="dialog" aria-modal="true"` and implemented none
 *  of this — so Tab walked straight out of the dialog into the page behind it, Escape did nothing,
 *  and closing dropped focus at the top of the document. Announcing a contract to assistive
 *  technology and then not honouring it is worse than not announcing it. */
export function useDialog(
  open: boolean,
  ref: RefObject<HTMLElement | null>,
  onClose: () => void,
): void {
  useEffect(() => {
    if (!open) return
    const opener = document.activeElement as HTMLElement | null
    const node = ref.current

    document.body.classList.add('ux4g-drawer-lock')
    // Move focus into the dialog so the next Tab stays inside it.
    node?.querySelector<HTMLElement>(FOCUSABLE)?.focus()

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose()
        return
      }
      if (event.key !== 'Tab' || !node) return

      const items = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null,
      )
      if (!items.length) return

      const first = items[0]
      const last = items[items.length - 1]
      const active = document.activeElement

      if (event.shiftKey && (active === first || !node.contains(active))) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      document.body.classList.remove('ux4g-drawer-lock')
      // Returning focus to whatever opened the dialog is the half most implementations forget.
      opener?.focus?.()
    }
  }, [open, ref, onClose])
}
