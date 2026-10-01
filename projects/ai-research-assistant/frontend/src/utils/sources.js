/**
 * Source normalization utility.
 *
 * Normalizes backend retrieval source metadata into a consistent
 * schema for the frontend presentation layer.
 */

export function normalizeSource(source, index = 0) {
  if (!source) {
    return {
      id: `S${index + 1}`,
      documentId: null,
      filename: "Unknown document",
      chunkIndex: 0,
      page: null,
      score: null,
    };
  }

  const rawScore =
    typeof source.score === "number"
      ? source.score
      : typeof source.reranker_score === "number"
      ? source.reranker_score
      : typeof source.vector_score === "number"
      ? source.vector_score
      : null;

  return {
    id: source.id || `S${index + 1}`,
    documentId: source.documentId ?? source.document_id ?? null,
    filename: source.filename || source.document || "Unknown document",
    chunkIndex: source.chunkIndex ?? source.chunk_index ?? source.chunk_id ?? 0,
    page: source.page ?? null,
    score: rawScore,
  };
}
