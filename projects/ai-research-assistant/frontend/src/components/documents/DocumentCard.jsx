export default function DocumentCard({
  document,
  onRetry,
  onDelete,
  retrying,
  deleting,
}) {
  const {
    id,
    filename,
    status,
    chunks,
    error_message,
  } = document;

  return (
    <article className="document-card">
      <div className="document-main">
        <div className="document-icon">
          PDF
        </div>

        <div className="document-info">
          <h3>{filename}</h3>

          {status === "processing" && (
            <p>Processing document...</p>
          )}

          {status === "indexed" && (
            <p>{chunks ?? 0} chunks indexed</p>
          )}

          {status === "failed" && (
            <p className="document-error">
              {error_message || "Document processing failed."}
            </p>
          )}
        </div>
      </div>

      <div className="document-actions">
        {status === "processing" && (
          <span className="status-badge processing">
            Processing
          </span>
        )}

        {status === "indexed" && (
          <span className="status-badge indexed">
            Ready for research
          </span>
        )}

        {status === "failed" && (
          <>
            <span className="status-badge failed">
              Failed
            </span>

            <button
              type="button"
              className="document-action-btn retry-btn"
              disabled={retrying}
              onClick={() => onRetry(id)}
            >
              {retrying ? "Retrying..." : "Retry"}
            </button>
          </>
        )}

        <button
          type="button"
          className="document-action-btn delete-btn"
          disabled={deleting}
          onClick={() => onDelete(id)}
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </article>
  );
}
