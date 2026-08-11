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

// getUserMedia rejects with a specific, named error — unlike SpeechRecognition's own error
// event, which often reports an unhelpful generic "no-speech" when the real cause is that the
// OS or browser silently blocked mic access before any audio could ever reach the recognizer.
// Checking permission explicitly first lets us tell the user the *actual* problem.
const MEDIA_ERROR_MESSAGES = {
  NotAllowedError:
    "Microphone access is blocked. Check your browser's site permissions for this page AND your operating system's microphone privacy settings, then try again.",
  PermissionDeniedError:
    "Microphone access is blocked. Check your browser's site permissions for this page AND your operating system's microphone privacy settings, then try again.",
  NotFoundError: 'No microphone was found on this device. Connect one and try again.',
  NotReadableError: 'Your microphone is being used by another app, or is not accessible right now. Close other apps using it and try again.',
  default: 'Could not access your microphone. Check your browser and system microphone permissions.',
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
    async (onTranscriptUpdate, onFinalTranscript) => {
      const SpeechRecognitionCtor = getSpeechRecognitionCtor()
      if (!SpeechRecognitionCtor || isListening) return

      setRecognitionError(null)

      // Confirm mic access explicitly before handing off to SpeechRecognition.
      // recognition.start() also implicitly requests mic access, but its own error event
      // often can't tell "the OS/browser silently blocked the mic" apart from "genuinely
      // heard nothing" — both can surface as a generic "no-speech" error, which is exactly
      // the confusing symptom of a real permission problem. getUserMedia rejects with a
      // specific, named error instead, so this catches the real cause up front.
      if (navigator.mediaDevices?.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          stream.getTracks().forEach((track) => track.stop())
        } catch (err) {
          setRecognitionError(MEDIA_ERROR_MESSAGES[err.name] || MEDIA_ERROR_MESSAGES.default)
          return
        }
      }

      const recognition = new SpeechRecognitionCtor()
      recognition.lang = navigator.language || 'en-US'
      recognition.interimResults = true
      recognition.continuous = true

      lastTranscriptRef.current = ''

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
        // A transcript here only ever hands off to the caller for review — it is never
        // auto-submitted by this hook. That matters because raw speech-to-text can be
        // incomplete or mis-heard (accents, background noise, a pause mid-thought); the
        // caller shows it back to the user to confirm or edit rather than sending it
        // straight to the AI, which is what used to produce a confusing "I didn't get an
        // answer" reply from the AI even when the user genuinely had spoken.
        if (transcript) {
          onFinalTranscript?.(transcript)
        } else {
          // Recognition ended with literally nothing captured (e.g. it decided the mic
          // was silent) but didn't fire a formal error event — show the same message a
          // real "no-speech" error would, instead of silently doing nothing and leaving
          // the user unsure whether they were heard at all.
          setRecognitionError(RECOGNITION_ERROR_MESSAGES['no-speech'])
        }
      }
      recognition.onerror = (event) => {
        setIsListening(false)
        // "aborted" is what fires when the user (or our own code) intentionally
        // stops recognition — not a real failure, so it shouldn't show an error.
        if (event.error === 'aborted') return

        // Some speech was already captured before this error interrupted recognition
        // (e.g. a transient "network" hiccup partway through an answer) — hand off what
        // was heard so far for the user to review/finish, rather than discarding real
        // speech just because the session didn't end cleanly.
        const partial = lastTranscriptRef.current.trim()
        if (partial) {
          onFinalTranscript?.(partial)
          return
        }
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
