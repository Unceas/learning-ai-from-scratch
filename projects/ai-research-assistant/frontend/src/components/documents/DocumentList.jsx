import { groupDocuments } from "../../utils/documents";
import DocumentCard from "./DocumentCard";

export default function DocumentList({
  documents,
  onRetry,
  onDelete,
  retryingId,
  deletingId,
}) {
  const groups = groupDocuments(documents);

  return (
    <div className="document-groups">
      <DocumentGroup
        title="Processing"
        documents={groups.processing}
        onRetry={onRetry}
        onDelete={onDelete}
        retryingId={retryingId}
        deletingId={deletingId}
      />

      <DocumentGroup
        title="Indexed"
        documents={groups.indexed}
        onRetry={onRetry}
        onDelete={onDelete}
        retryingId={retryingId}
        deletingId={deletingId}
      />

      <DocumentGroup
        title="Failed"
        documents={groups.failed}
        onRetry={onRetry}
        onDelete={onDelete}
        retryingId={retryingId}
        deletingId={deletingId}
      />
    </div>
  );
}

function DocumentGroup({
  title,
  documents,
  onRetry,
  onDelete,
  retryingId,
  deletingId,
}) {
  if (!documents.length) {
    return null;
  }

  return (
    <section className="document-group">
      <h2>{title} ({documents.length})</h2>

      <div className="document-list">
        {documents.map((document) => (
          <DocumentCard
            key={document.id}
            document={document}
            onRetry={onRetry}
            onDelete={onDelete}
            retrying={retryingId === document.id}
            deleting={deletingId === document.id}
          />
        ))}
      </div>
    </section>
  );
}
