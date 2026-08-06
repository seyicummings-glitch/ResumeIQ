import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, cleanup } from '@testing-library/react'
import { useSpeechVoice } from './useSpeechVoice'

describe('useSpeechVoice — unsupported browser', () => {
  it('reports both APIs as unsupported and no-ops speak/startListening without throwing', () => {
    const { result } = renderHook(() => useSpeechVoice())

    expect(result.current.recognitionSupported).toBe(false)
    expect(result.current.synthesisSupported).toBe(false)

    expect(() => {
      act(() => {
        result.current.speak('hello')
        result.current.startListening(() => {})
      })
    }).not.toThrow()

    expect(result.current.isListening).toBe(false)
    expect(result.current.isSpeaking).toBe(false)
  })
})

describe('useSpeechVoice — supported browser (mocked Web Speech API)', () => {
  let utteranceInstances
  let recognitionInstances

  beforeEach(() => {
    utteranceInstances = []
    recognitionInstances = []

    global.SpeechSynthesisUtterance = vi.fn().mockImplementation(function (text) {
      this.text = text
      utteranceInstances.push(this)
    })

    global.speechSynthesis = {
      cancel: vi.fn(),
      speak: vi.fn((utterance) => utterance.onstart?.()),
    }
    global.window.speechSynthesis = global.speechSynthesis

    function FakeRecognition() {
      this.start = vi.fn()
      this.stop = vi.fn(() => this.onend?.())
      recognitionInstances.push(this)
    }
    global.window.SpeechRecognition = FakeRecognition
  })

  afterEach(() => {
    // Unmount every rendered hook first, while the mocked APIs still exist — the
    // hook's own unmount effect calls window.speechSynthesis.cancel(), so removing
    // the mocks before unmounting makes that cleanup throw.
    cleanup()
    delete global.window.speechSynthesis
    delete global.window.SpeechRecognition
    delete global.speechSynthesis
    delete global.SpeechSynthesisUtterance
    vi.restoreAllMocks()
  })

  it('reports both APIs as supported', () => {
    const { result } = renderHook(() => useSpeechVoice())
    expect(result.current.recognitionSupported).toBe(true)
    expect(result.current.synthesisSupported).toBe(true)
  })

  it('speak() cancels any prior utterance and speaks the new one', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.speak('Tell me about a recent project.')
    })

    expect(global.speechSynthesis.cancel).toHaveBeenCalled()
    expect(global.speechSynthesis.speak).toHaveBeenCalledTimes(1)
    expect(utteranceInstances[0].text).toBe('Tell me about a recent project.')
    expect(result.current.isSpeaking).toBe(true)
  })

  it('speak() does nothing for empty text', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.speak('')
    })

    expect(global.speechSynthesis.speak).not.toHaveBeenCalled()
  })

  it('stopSpeaking() cancels synthesis and clears isSpeaking', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.speak('hello')
    })
    expect(result.current.isSpeaking).toBe(true)

    act(() => {
      result.current.stopSpeaking()
    })
    expect(result.current.isSpeaking).toBe(false)
    expect(global.speechSynthesis.cancel).toHaveBeenCalledTimes(2)
  })

  it('startListening() starts recognition and sets isListening', () => {
    const { result } = renderHook(() => useSpeechVoice())
    const onTranscriptUpdate = vi.fn()

    act(() => {
      result.current.startListening(onTranscriptUpdate)
    })

    expect(result.current.isListening).toBe(true)
  })

  it('calls onTranscriptUpdate on every result and onFinalTranscript once recognition ends', () => {
    const { result } = renderHook(() => useSpeechVoice())
    const onTranscriptUpdate = vi.fn()
    const onFinalTranscript = vi.fn()

    act(() => {
      result.current.startListening(onTranscriptUpdate, onFinalTranscript)
    })

    const recognition = recognitionInstances[0]
    act(() => {
      recognition.onresult({ results: [[{ transcript: 'I built ' }]] })
      recognition.onresult({ results: [[{ transcript: 'I built a REST API' }]] })
    })
    expect(onTranscriptUpdate).toHaveBeenLastCalledWith('I built a REST API')
    expect(onFinalTranscript).not.toHaveBeenCalled()

    act(() => {
      recognition.onend()
    })
    expect(onFinalTranscript).toHaveBeenCalledWith('I built a REST API')
    expect(result.current.isListening).toBe(false)
  })

  it('does not call onFinalTranscript when nothing was transcribed', () => {
    const { result } = renderHook(() => useSpeechVoice())
    const onFinalTranscript = vi.fn()

    act(() => {
      result.current.startListening(() => {}, onFinalTranscript)
    })
    act(() => {
      recognitionInstances[0].onend()
    })

    expect(onFinalTranscript).not.toHaveBeenCalled()
  })

  it('does not construct a second recognition instance while already listening', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.startListening(() => {})
    })
    expect(recognitionInstances).toHaveLength(1)

    act(() => {
      result.current.startListening(() => {})
    })
    expect(recognitionInstances).toHaveLength(1)
  })

  it('stopListening() calls stop() on the active recognition, which clears isListening via onend', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.startListening(() => {})
    })
    expect(result.current.isListening).toBe(true)

    act(() => {
      result.current.stopListening()
    })
    expect(result.current.isListening).toBe(false)
  })

  it('onerror surfaces a user-facing message instead of failing silently', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.startListening(() => {})
    })
    const recognition = recognitionInstances[0]

    act(() => {
      recognition.onerror({ error: 'not-allowed' })
    })

    expect(result.current.isListening).toBe(false)
    expect(result.current.recognitionError).toMatch(/microphone access was denied/i)
  })

  it('onerror with "aborted" (an intentional stop) does not set a visible error', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.startListening(() => {})
    })
    const recognition = recognitionInstances[0]

    act(() => {
      recognition.onerror({ error: 'aborted' })
    })

    expect(result.current.recognitionError).toBe(null)
  })

  it('starting a new listening session clears a previous error', () => {
    const { result } = renderHook(() => useSpeechVoice())

    act(() => {
      result.current.startListening(() => {})
    })
    act(() => {
      recognitionInstances[0].onerror({ error: 'network' })
    })
    expect(result.current.recognitionError).not.toBe(null)

    act(() => {
      result.current.startListening(() => {})
    })
    expect(result.current.recognitionError).toBe(null)
  })
})
