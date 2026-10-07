/**
 * SourceCard component.
 *
 * Clickable source provenance card with DOM target ID for smooth scrolling,
 * selected highlighting, filename, chunk metadata, and score representation.
 */

export default function SourceCard({
  source,
  index = 0,
  selected = false,
  onClick,
}) {
  const sourceId = source.id || `S${index + 1}`;
  const docId = source.document_id ?? source.documentId ?? "—";
  const chunkIdx = source.chunk_index ?? source.chunkIndex ?? 0;

  return (
    <button
      type="button"
      id={`source-${sourceId}`}
      className={`source-card ${selected ? "source-card-selected" : ""}`}
      onClick={() => onClick?.(sourceId)}
    >
      <div className="source-card-header">
        <span className="source-id">
          [{sourceId}]
        </span>

        <span className="source-filename">
          {source.filename}
        </span>
      </div>

      <div className="source-card-meta">
        <span>Document {docId}</span>
        <span>Chunk {chunkIdx}</span>

        {source.score !== undefined && source.score !== null && (
          <span>
            Score: {typeof source.score === "number" ? source.score.toFixed(3) : source.score}
          </span>
        )}
      </div>
    </button>
  );
}
