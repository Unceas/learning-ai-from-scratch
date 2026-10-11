/**
 * SourcePreview component.
 *
 * Dedicated inspection panel displaying authorized retrieved passage excerpt,
 * document filename, chunk identifier, and retrieval score.
 */

export default function SourcePreview({
  source,
  onClose,
}) {
  if (!source) return null;

  const docId = source.document_id ?? source.documentId ?? "—";
  const chunkIdx = source.chunk_index ?? source.chunkIndex ?? 0;
  const rawScore =
    source.score !== undefined && source.score !== null
      ? Number(source.score)
      : null;

  return (
    <aside
      className="source-preview"
      aria-label="Source details"
    >
      <header className="source-preview-header">
        <div>
          <span className="source-preview-label">
            Source details
          </span>

          <h2>{source.filename || "Unknown document"}</h2>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close source details"
        >
          Close
        </button>
      </header>

      <div className="source-preview-metadata">
        <p>Document ID: {docId}</p>
        <p>Chunk: {chunkIdx}</p>

        {rawScore !== null && !Number.isNaN(rawScore) && (
          <p>
            Retrieval score: {rawScore.toFixed(3)}
          </p>
        )}
      </div>

      <section className="source-preview-content">
        <h3>Retrieved passage</h3>

        <blockquote>
          {source.text || "No passage text is available."}
        </blockquote>
      </section>
    </aside>
  );
}
