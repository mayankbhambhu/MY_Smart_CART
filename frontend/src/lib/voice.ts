import { useCallback, useEffect, useRef, useState } from 'react'

// Minimal typing for the Web Speech API (Chrome/Edge/Safari expose it as webkitSpeechRecognition).
interface RecognitionEvent {
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>
}
interface Recognition {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((event: RecognitionEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}
type RecognitionConstructor = new () => Recognition

function recognitionConstructor(): RecognitionConstructor | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor
    webkitSpeechRecognition?: RecognitionConstructor
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

/** Speech-to-text for the shopping list. Indian English handles "doodh", "atta", "maggi" well. */
export function useVoiceInput(onTranscript: (text: string, isFinal: boolean) => void) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recognition = useRef<Recognition | null>(null)
  const callback = useRef(onTranscript)

  useEffect(() => {
    callback.current = onTranscript
  }, [onTranscript])

  useEffect(() => () => recognition.current?.abort(), [])

  const start = useCallback(() => {
    const Ctor = recognitionConstructor()
    if (!Ctor) return
    const rec = new Ctor()
    rec.lang = 'en-IN'
    rec.interimResults = true
    rec.continuous = false // one spoken list per tap; it stops when the shopper pauses
    rec.onresult = (event) => {
      let text = ''
      let isFinal = true
      for (let i = 0; i < event.results.length; i++) {
        text += event.results[i][0].transcript
        if (!event.results[i].isFinal) isFinal = false
      }
      callback.current(text.trim(), isFinal)
    }
    rec.onerror = (event) => {
      setError(
        event.error === 'not-allowed' || event.error === 'service-not-allowed'
          ? 'Microphone access is blocked. Allow it in your browser settings.'
          : "Didn't catch that. Tap the mic and try again.",
      )
    }
    rec.onend = () => setListening(false)
    recognition.current = rec
    setError(null)
    setListening(true)
    rec.start()
  }, [])

  const stop = useCallback(() => recognition.current?.stop(), [])

  return { supported: recognitionConstructor() !== null, listening, error, start, stop }
}
