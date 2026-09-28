import { apiFetch } from "./client";

/**
 * Retrieve all registered research documents for the authenticated user.
 */
export function getDocuments() {
  return apiFetch("/api/documents/");
}

/**
 * Get current processing/indexing status for a specific document.
 *
 * @param {number} id - Document ID.
 */
export function getDocumentStatus(id) {
  return apiFetch(`/api/documents/${id}`);
}

/**
 * Retry background processing for a failed document.
 *
 * @param {number} id - Document ID.
 */
export function retryDocument(id) {
  return apiFetch(`/api/documents/${id}/retry`, {
    method: "POST",
  });
}

/**
 * Delete a document by file hash across storage, database, and vector index.
 *
 * @param {string} fileHash - Document SHA-256 hash.
 */
export function deleteDocument(fileHash) {
  return apiFetch(`/api/documents/${fileHash}`, {
    method: "DELETE",
  });
}

/**
 * Upload a PDF document for background chunking and vector indexing.
 *
 * @param {File} file - PDF File instance.
 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch("/api/documents/upload", {
    method: "POST",
    body: formData,
  });
}
