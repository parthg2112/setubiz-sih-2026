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
      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary" role="status">
        {strings.micUnsupported}
      </p>
    )
  }

  /* Text label always visible beside the icon: a microphone glyph alone is not a word, and this
     control is the one a reader who cannot type comfortably depends on most. */
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={listening}
      className={`ux4g-btn ${
        listening ? 'ux4g-btn-danger' : 'ux4g-btn-tonal-primary'
      } ux4g-btn-lg ux4g-gap-x-xs setubiz-no-print`}
    >
      <span className="ux4g-icon-outlined" aria-hidden="true">
        {listening ? 'stop_circle' : 'mic'}
      </span>
      {listening ? strings.listening : strings.speak}
    </button>
  )
}
