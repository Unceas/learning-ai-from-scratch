import { apiFetch } from "./client";

/**
 * Retrieve an authorized source chunk excerpt and metadata for a specific document and chunk index.
 *
 * @param {number} documentId - Document ID.
 * @param {number} chunkIndex - Chunk index.
 * @returns {Promise<Object>} Chunk details including text, filename, and metadata.
 */
export function getDocumentChunk(documentId, chunkIndex) {
  return apiFetch(`/api/documents/${documentId}/chunks/${chunkIndex}`);
}
