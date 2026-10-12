import { apiFetch } from "./client";

/**
 * Submit or update user feedback for a persisted assistant message.
 *
 * @param {Object} payload - { message_id, rating, reason, comment }
 * @returns {Promise<Object>} Feedback record
 */
export function submitFeedback(payload) {
  return apiFetch("/api/feedback", {
    method: "POST",
    body: typeof payload === "string" ? payload : JSON.stringify(payload),
  });
}

/**
 * Retrieve aggregated feedback summary metrics for the current user.
 *
 * @returns {Promise<Object>} Summary { helpful, not_helpful, total }
 */
export function getFeedbackSummary() {
  return apiFetch("/api/feedback/summary");
}

/**
 * Retrieve existing feedback for a specific assistant message.
 *
 * @param {number} messageId - Database message ID
 * @returns {Promise<Object>} Feedback record
 */
export function getMessageFeedback(messageId) {
  return apiFetch(`/api/feedback/${messageId}`);
}
