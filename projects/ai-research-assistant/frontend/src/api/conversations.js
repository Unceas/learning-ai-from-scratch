import { apiFetch } from "./client";

/**
 * List all conversation sessions for the authenticated user.
 */
export function getConversations() {
  return apiFetch("/api/conversations");
}

/**
 * Retrieve a specific conversation and its turn history.
 *
 * @param {number} id - Conversation ID.
 */
export function getConversation(id) {
  return apiFetch(`/api/conversations/${id}`);
}

/**
 * Create a new conversation session.
 *
 * @param {string|null} [title=null] - Optional conversation preview title.
 */
export function createConversation(title = null) {
  return apiFetch("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

/**
 * Delete a conversation and all cascaded dialogue messages.
 *
 * @param {number} id - Conversation ID.
 */
export function deleteConversation(id) {
  return apiFetch(`/api/conversations/${id}`, {
    method: "DELETE",
  });
}

/**
 * Retrieve paginated message history for a conversation.
 *
 * @param {number} id - Conversation ID.
 * @param {number} [limit=50] - Number of messages to fetch.
 * @param {number} [offset=0] - Offset for pagination.
 */
export function getConversationMessages(id, limit = 50, offset = 0) {
  return apiFetch(`/api/conversations/${id}/messages?limit=${limit}&offset=${offset}`);
}
