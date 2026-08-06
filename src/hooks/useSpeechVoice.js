import { useCallback, useEffect, useRef, useState } from 'react'

function getSpeechRecognitionCtor() {
  return typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null
}

// Maps the native SpeechRecognitionErrorEvent.error codes to a message a user
// can actually act on — previously these were swallowed entirely, so a failed
// recognition attempt (e.g. mic permission denied) looked identical to "you
// tapped the mic and nothing happened."
const RECOGNITION_ERROR_MESSAGES = {
  'no-speech': "Didn't catch that — no speech was detected. Tap the mic and try again.",
  'audio-capture': 'No microphone was found. Check that one is connected and enabled, then try again.',
  'not-allowed': "Microphone access was denied. Check your browser's site permissions for this page and try again.",
  'service-not-allowed': "Microphone access was denied. Check your browser's site permissions for this page and try again.",
  network: 'A network error interrupted speech recognition. Try again.',
  default: 'Something went wrong with speech recognition. Try again, or switch to text.',
}

/**
 * Thin wrapper around the browser's native Web Speech API — no backend, no API cost.
 * Speech-to-text (SpeechRecognition) has real support only in Chromium-based browsers;
 * text-to-speech (speechSynthesis) is much more broadly supported. Both are feature-detected
 * so callers can hide/disable controls gracefully where unsupported. Support is checked live
 * (not cached at module-load time) so it reflects the actual browser at call time.
 */
export function useSpeechVoice() {
  const recognitionSupported = Boolean(getSpeechRecognitionCtor())
  const synthesisSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [recognitionError, setRecognitionError] = useState(null)
  const recognitionRef = useRef(null)
  const lastTranscriptRef = useRef('')

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
      if (synthesisSupported) window.speechSynthesis.cancel()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const speak = useCallback(
    (text) => {
      if (!synthesisSupported || !text) return
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = navigator.language || 'en-US'
      utterance.onstart = () => setIsSpeaking(true)
      utterance.onend = () => setIsSpeaking(false)
      utterance.onerror = () => setIsSpeaking(false)
      window.speechSynthesis.speak(utterance)
    },
    [synthesisSupported]
  )

  const stopSpeaking = useCallback(() => {
    if (synthesisSupported) window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }, [synthesisSupported])

  /**
   * onTranscriptUpdate fires on every partial/final result with the current best transcript
   * (for live captioning). onFinalTranscript fires once recognition actually stops — either
   * because the caller called stopListening() (the normal "tap again to stop and send" flow)
   * or the browser ended it on its own (e.g. a real error) — with whatever was transcribed.
   *
   * continuous=true is intentional: with continuous=false, Chrome applies a short internal
   * "no speech" timeout and gives up if the user doesn't start talking within a couple of
   * seconds of tapping the mic (e.g. taking a moment to think), firing a confusing "no speech
   * detected" error even though the user genuinely answered a moment later. continuous=true
   * keeps listening — across pauses too — until the user explicitly taps to stop, matching
   * what the UI already tells them to do.
   */
  const startListening = useCallback(
    (onTranscriptUpdate, onFinalTranscript) => {
      const SpeechRecognitionCtor = getSpeechRecognitionCtor()
      if (!SpeechRecognitionCtor || isListening) return
      const recognition = new SpeechRecognitionCtor()
      recognition.lang = navigator.language || 'en-US'
      recognition.interimResults = true
      recognition.continuous = true

      lastTranscriptRef.current = ''
      setRecognitionError(null)

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join('')
        lastTranscriptRef.current = transcript
        onTranscriptUpdate?.(transcript)
      }
      recognition.onend = () => {
        setIsListening(false)
        const transcript = lastTranscriptRef.current.trim()
        if (transcript) onFinalTranscript?.(transcript)
      }
      recognition.onerror = (event) => {
        setIsListening(false)
        // "aborted" is what fires when the user (or our own code) intentionally
        // stops recognition — not a real failure, so it shouldn't show an error.
        if (event.error === 'aborted') return
        setRecognitionError(RECOGNITION_ERROR_MESSAGES[event.error] || RECOGNITION_ERROR_MESSAGES.default)
      }

      recognitionRef.current = recognition
      recognition.start()
      setIsListening(true)
    },
    [recognitionSupported, isListening]
  )

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  return {
    recognitionSupported,
    synthesisSupported,
    isListening,
    isSpeaking,
    recognitionError,
    speak,
    stopSpeaking,
    startListening,
    stopListening,
  }
}
