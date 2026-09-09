import { useEffect, useRef, useState } from 'react'

interface Props {
  onResult: (transcript: string) => void
  language: 'en' | 'hi'
  strings: { speak: string; listening: string; micUnsupported: string }
}

interface SpeechRecognitionLike extends EventTarget {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  start(): void
  stop(): void
  onresult: ((event: { results: { 0: { 0: { transcript: string } } } }) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
}

type Ctor = new () => SpeechRecognitionLike

function recognizer(): Ctor | null {
  const w = window as unknown as { SpeechRecognition?: Ctor; webkitSpeechRecognition?: Ctor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

/** Voice input stub. The browser's Web Speech API stands in for the Indic ASR lane; it degrades
 *  to typing without complaint, which is the behaviour the real deployment needs anyway. */
export function MicButton({ onResult, language, strings }: Props) {
  const [listening, setListening] = useState(false)
  const [supported, setSupported] = useState(true)
  const ref = useRef<SpeechRecognitionLike | null>(null)

  useEffect(() => {
    setSupported(recognizer() !== null)
    return () => ref.current?.stop()
  }, [])

  function toggle() {
    if (listening) {
      ref.current?.stop()
      setListening(false)
      return
    }
    const Ctor = recognizer()
    if (!Ctor) {
      setSupported(false)
      return
    }
    const instance = new Ctor()
    instance.lang = language === 'hi' ? 'hi-IN' : 'en-IN'
    instance.interimResults = false
    instance.maxAlternatives = 1
    instance.onresult = (event) => onResult(event.results[0][0].transcript)
    instance.onerror = () => setListening(false)
    instance.onend = () => setListening(false)
    ref.current = instance
    instance.start()
    setListening(true)
  }

  if (!supported) {
    return (
      <p className="mt-1 text-xs text-subtle-foreground" role="status">
        {strings.micUnsupported}
      </p>
    )
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={listening}
      className="no-print inline-flex shrink-0 items-center gap-2 rounded-lg border px-3 py-3 text-sm font-medium transition-colors"
      style={{
        borderColor: listening ? 'var(--destructive)' : 'var(--border)',
        color: listening ? 'var(--destructive)' : 'var(--muted-foreground)',
      }}
    >
      <span aria-hidden>{listening ? '●' : '🎙'}</span>
      {listening ? strings.listening : strings.speak}
    </button>
  )
}
