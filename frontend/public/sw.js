/*
 * Aatmanirbhar Local Vyapar service worker: the offline shell for a low-connectivity village session.
 *
 * Three strategies, deliberately small:
 *  - App shell (navigations): serve the cached index.html immediately and refresh it in the
 *    background, so a dropped connection mid-session never blanks the app.
 *  - GET /api/* (village search, cost templates, schemes): network-first with a cache fallback.
 *  - POST /api/v1/advisory: network-first; every successful report is cached under a key derived
 *    from its request body. Report inputs live entirely in the URL, so reopening the same report
 *    link offline replays the saved response and the full report renders with no network.
 *
 * The SW never touches report numbers: a cached report is the exact bytes the server produced,
 * already validated by the numeric-grounding layer.
 */

const VERSION = 'setubiz-v1'
const SHELL = `${VERSION}-shell`
const RUNTIME = `${VERSION}-runtime`
const ADVISORY_PATH = '/api/v1/advisory'

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL)
      await cache.addAll(['/', '/index.html', '/manifest.webmanifest'])
      await self.skipWaiting()
    })(),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys()
      await Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)))
      await self.clients.claim()
    })(),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  const url = new URL(req.url)
  if (url.origin !== self.location.origin) return

  if (req.method === 'POST' && url.pathname === ADVISORY_PATH) {
    event.respondWith(handleAdvisory(req))
    return
  }
  if (req.method !== 'GET') return

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(req, RUNTIME))
    return
  }
  if (req.mode === 'navigate') {
    event.respondWith(shellFirst(req))
    return
  }
  event.respondWith(cacheFirst(req))
})

async function handleAdvisory(req) {
  const copy = req.clone()
  try {
    const res = await fetch(req)
    if (res.ok) {
      const body = await copy.text()
      const cache = await caches.open(RUNTIME)
      await cache.put(advisoryKey(req.url, body), res.clone())
    }
    return res
  } catch (err) {
    const body = await copy.text()
    const hit = await caches.match(advisoryKey(req.url, body))
    if (hit) return hit
    return new Response(
      JSON.stringify({
        detail:
          'You are offline and this report is not saved on this device yet. Reconnect once, or reopen a report you viewed earlier.',
      }),
      { status: 503, headers: { 'Content-Type': 'application/json' } },
    )
  }
}

async function networkFirst(req, cacheName) {
  try {
    const res = await fetch(req)
    if (res.ok) {
      const cache = await caches.open(cacheName)
      await cache.put(req, res.clone())
    }
    return res
  } catch (err) {
    const hit = await caches.match(req)
    if (hit) return hit
    throw err
  }
}

async function shellFirst(req) {
  const cache = await caches.open(SHELL)
  const cached = await cache.match('/index.html')
  const refresh = fetch(req).then((res) => {
    if (res.ok) cache.put('/index.html', res.clone())
    return res
  })
  return cached || refresh
}

async function cacheFirst(req) {
  const hit = await caches.match(req)
  if (hit) return hit
  const res = await fetch(req)
  if (res.ok) {
    const cache = await caches.open(SHELL)
    await cache.put(req, res.clone())
  }
  return res
}

/* Cache key for a report: the advisory URL plus a digest of the exact request body, so two
   different inputs on the same URL never collide and the same link always replays the same
   report. djb2 is enough for that; this is a cache key, not a security boundary. */
function advisoryKey(url, body) {
  let h = 5381
  for (let i = 0; i < body.length; i++) h = ((h << 5) + h + body.charCodeAt(i)) | 0
  return `${url}?__report=${h >>> 0}`
}
