export default function DocumentCard({
  document,
  onRetry,
  onDelete,
}) {
  const {
    id,
    filename,
    chunks,
    status,
    error_message,
  } = document;

  return (
    <article className="document-card">
      <div className="document-main">
        <h3>{filename}</h3>

        <div className="document-meta">
          {status === "indexed" && (
            <span>
              {chunks} chunks
            </span>
          )}

          {status === "processing" && (
            <span>
              Processing...
            </span>
          )}

          {status === "failed" && (
            <span>
              Processing failed
            </span>
          )}
        </div>

        {error_message && (
          <p className="document-error">
            {error_message}
          </p>
        )}
      </div>

      <div className="document-actions">
        {status === "failed" && (
          <button
            type="button"
            onClick={() => onRetry(id)}
          >
            Retry
          </button>
        )}

        <button
          type="button"
          onClick={() => onDelete(id)}
        >
          Delete
        </button>
      </div>
    </article>
  );
}
