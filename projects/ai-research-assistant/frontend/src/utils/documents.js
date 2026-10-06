/**
 * Document state normalization and grouping utilities.
 *
 * Provides stable document lifecycle status resolution, semantic UI labels,
 * and categorization into Processing, Indexed, and Failed collections.
 */

export function getDocumentStatus(document) {
  if (!document) return "unknown";

  switch (document.status) {
    case "processing":
      return "processing";
    case "indexed":
      return "indexed";
    case "failed":
      return "failed";
    default:
      return "unknown";
  }
}

export function groupDocuments(documents = []) {
  const safeDocs = Array.isArray(documents) ? documents : [];

  return {
    processing: safeDocs.filter((doc) => doc.status === "processing"),
    indexed: safeDocs.filter((doc) => doc.status === "indexed"),
    failed: safeDocs.filter((doc) => doc.status === "failed"),
  };
}

export function getStatusLabel(status) {
  switch (status) {
    case "processing":
      return "Processing document...";
    case "indexed":
      return "Ready for research";
    case "failed":
      return "Processing failed";
    default:
      return "Unknown state";
  }
}
