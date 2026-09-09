import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Self-hosted, per-subset: the app has to render on a rural connection with no CDN reachable.
import '@fontsource/open-sans/latin-400.css'
import '@fontsource/open-sans/latin-600.css'
import '@fontsource/open-sans/latin-700.css'
// Devanagari carries a unicode-range, so an English session never fetches these ~50 KB faces.
import '@fontsource/noto-sans-devanagari/devanagari-400.css'
import '@fontsource/noto-sans-devanagari/devanagari-600.css'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
