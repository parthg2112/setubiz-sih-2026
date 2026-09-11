import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// UX4G owns every component, token and utility in this app. Loaded once, here, per the package
// contract: the package exports no React components, only CSS classes and a runtime side effect.
import 'ux4g-web-components/styles.css'
import 'ux4g-web-components/design-system'
// UX4G embeds Noto Sans and the Material Icons faces but ships no Devanagari, so Hindi still
// needs its own. The unicode-range keeps an English session from fetching these ~50 KB faces.
import '@fontsource/noto-sans-devanagari/devanagari-400.css'
import '@fontsource/noto-sans-devanagari/devanagari-600.css'
import App from './App'
import './app.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
