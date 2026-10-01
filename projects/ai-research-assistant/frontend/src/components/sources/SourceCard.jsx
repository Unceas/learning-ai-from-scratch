/**
 * SourceCard component.
 *
 * Renders individual source provenance details, metadata, and retrieval score.
 */

export default function SourceCard({ source }) {
  const score =
    typeof source.score === "number"
      ? source.score.toFixed(3)
      : null;

  return (
    <article className="source-card">
      <div className="source-card-header">
        <span className="source-id">
          [{source.id}]
        </span>

        <span className="source-filename">
          {source.filename}
        </span>

        {score !== null && (
          <span className="source-score">
            Score {score}
          </span>
        )}
      </div>

      <div className="source-metadata">
        <span>
          Document {source.documentId ?? "—"}
        </span>

        <span>
          Chunk {source.chunkIndex ?? 0}
        </span>

        {source.page !== null && source.page !== undefined && (
          <span>
            Page {source.page}
          </span>
        )}
      </div>
    </article>
  );
}
