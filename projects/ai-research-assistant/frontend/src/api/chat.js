import { apiFetch } from "./client";

/**
 * Send a research question to the RAG chat pipeline.
 *
 * @param {string} message - The research question or follow-up prompt.
 * @param {number|null} [conversationId=null] - Optional conversation session identifier.
 * @param {string|null} [filename=null] - Optional document scope filter.
 * @returns {Promise<Object>} Chat response with answer, sources, and conversation ID.
 */
export async function sendMessage(
  message,
  conversationId = null,
  filename = null
) {
  const payload = {
    message,
    conversation_id: conversationId,
  };

  if (filename) {
    payload.filename = filename;
  }

  return apiFetch("/api/chat/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
