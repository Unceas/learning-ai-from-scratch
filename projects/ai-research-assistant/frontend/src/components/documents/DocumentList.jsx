import DocumentCard from "./DocumentCard";

export default function DocumentList({
  documents,
  onRetry,
  onDelete,
}) {
  const processing = documents.filter(
    (document) =>
      document.status === "processing"
  );

  const indexed = documents.filter(
    (document) =>
      document.status === "indexed"
  );

  const failed = documents.filter(
    (document) =>
      document.status === "failed"
  );

  function renderGroup(title, items) {
    if (items.length === 0) {
      return null;
    }

    return (
      <section className="document-group">
        <h2>{title}</h2>

        <div>
          {items.map((document) => (
            <DocumentCard
              key={document.id}
              document={document}
              onRetry={onRetry}
              onDelete={onDelete}
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <div className="document-list">
      {renderGroup(
        "Processing",
        processing
      )}

      {renderGroup(
        "Indexed",
        indexed
      )}

      {renderGroup(
        "Failed",
        failed
      )}

      {documents.length === 0 && (
        <p className="empty-documents">No documents uploaded yet.</p>
      )}
    </div>
  );
}
