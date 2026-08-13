import { apiRequest, apiRequestBlob } from './client'

/**
 * @typedef {Object} InterviewQuestion
 * @property {number} id
 * @property {'Behavioral'|'Technical'|'System Design'|'Role-Specific'} category
 * @property {'Easy'|'Medium'|'Hard'} difficulty
 * @property {string} question
 * @property {string} tip
 * @property {string} sample_answer
 * @property {string} relevance
 *
 * @typedef {Object} InterviewQuestionsResult
 * @property {InterviewQuestion[]} questions
 * @property {boolean} has_analysis
 * @property {string} [jd_title]
 */

/** @returns {Promise<InterviewQuestionsResult>} */
export function getInterviewQuestions() {
  return apiRequest('/interview/questions', { auth: true })
}

/**
 * @typedef {Object} ChatMessage
 * @property {'interviewer'|'candidate'} role
 * @property {string} content
 *
 * @typedef {Object} InterviewChatReply
 * @property {string} feedback - critique of the candidate's previous answer; empty string on the first turn
 * @property {string} question - the next question, or closing remarks once done is true
 * @property {'ai'|'fallback'} source
 * @property {boolean} done
 */

/**
 * One turn of the live mock interview. Send the full transcript so far
 * (not including the reply being requested) and get the interviewer's next
 * message back — no server-side session, the frontend owns the transcript.
 * preferredLanguage (the browser's locale, e.g. navigator.language) seeds the
 * language of the interviewer's opening message; it then follows whatever
 * language the candidate actually writes in.
 * @param {{conversation: ChatMessage[], preferredLanguage: string | undefined, mode: 'voice' | 'text' | undefined}} params
 * @returns {Promise<InterviewChatReply>}
 */
export function sendInterviewMessage({ conversation, preferredLanguage, mode }) {
  return apiRequest('/interview/chat', {
    method: 'POST',
    auth: true,
    body: { conversation, preferred_language: preferredLanguage, mode },
  })
}

/**
 * @typedef {Object} InterviewFeedback
 * @property {string} overall_assessment
 * @property {number|null} overall_score - 0-100, or null when no AI was available to grade it
 * @property {string} technical_performance
 * @property {string} communication_assessment
 * @property {string} confidence_assessment
 * @property {string[]} strengths
 * @property {string[]} areas_to_improve
 * @property {string[]} recommended_improvements
 * @property {string[]} study_topics
 * @property {string[]} role_knowledge_tips
 * @property {'ai'|'fallback'} source
 *
 * @typedef {Object} SaveInterviewSessionResult
 * @property {number} id
 * @property {InterviewFeedback} feedback
 * @property {boolean} hasAudio
 */

/**
 * Persists a completed interview session — the full transcript and the recorded audio, if the
 * browser supported capturing it — and returns the AI-generated post-interview feedback report.
 * @param {{transcript: ChatMessage[], audioBlob: Blob | null, mode: 'voice' | 'text' | undefined}} params
 * @returns {Promise<SaveInterviewSessionResult>}
 */
export async function saveInterviewSession({ transcript, audioBlob, mode }) {
  const formData = new FormData()
  formData.append('transcript', JSON.stringify(transcript))
  if (audioBlob) {
    const extension = audioBlob.type.includes('mp4') ? 'mp4' : 'webm'
    formData.append('audio', audioBlob, `interview-recording.${extension}`)
  }
  if (mode) formData.append('mode', mode)

  const row = await apiRequest('/interview/sessions', { method: 'POST', auth: true, body: formData })
  return { id: row.id, feedback: row.feedback, hasAudio: row.has_audio }
}

/** Fetches a past session's recorded audio as a Blob, for local playback via an object URL. */
export function fetchInterviewSessionAudio(sessionId) {
  return apiRequestBlob(`/interview/sessions/${sessionId}/audio`, { auth: true })
}
