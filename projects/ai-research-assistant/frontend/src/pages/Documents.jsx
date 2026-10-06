import UploadDocument from "../components/documents/UploadDocument";
import DocumentList from "../components/documents/DocumentList";
import EmptyState from "../components/common/EmptyState";
import LoadingState from "../components/common/LoadingState";
import ErrorState from "../components/common/ErrorState";

import useDocuments from "../hooks/useDocuments";

export default function Documents() {
  const {
    documents,
    loading,
    uploading,
    error,
    upload,
    retry,
    remove,
    retryingId,
    deletingId,
    pollingTimedOut,
    fetchDocuments,
  } = useDocuments();

  const readyCount = documents.filter((doc) => doc.status === "indexed").length;
  const processingCount = documents.filter((doc) => doc.status === "processing").length;
  const failedCount = documents.filter((doc) => doc.status === "failed").length;

  async function handleDelete(id) {
    const confirmed = typeof window !== "undefined"
      ? window.confirm("Are you sure you want to delete this document? This will remove its indexed vectors and source data.")
      : true;

    if (!confirmed) {
      return;
    }

    await remove(id);
  }

  return (
    <div className="documents-page">
      <header className="documents-header">
        <div>
          <h1>Documents</h1>
          <p>
            Upload research papers and build your searchable knowledge base.
          </p>
          {documents.length > 0 && (
            <div className="documents-summary">
              <span>{documents.length} document{documents.length === 1 ? "" : "s"}</span>
              <span className="summary-dot">·</span>
              <span className="summary-ready">{readyCount} ready</span>
              <span className="summary-dot">·</span>
              <span className="summary-processing">{processingCount} processing</span>
              <span className="summary-dot">·</span>
              <span className="summary-failed">{failedCount} failed</span>
            </div>
          )}
        </div>
      </header>

      <UploadDocument
        onUpload={upload}
        uploading={uploading}
      />

      {pollingTimedOut && (
        <div className="processing-timeout-notice">
          Document ingestion is taking longer than expected. You can refresh the page or retry processing later.
        </div>
      )}

      {error && (
        <ErrorState
          message={error}
          onRetry={fetchDocuments}
        />
      )}

      {loading ? (
        <LoadingState message="Loading documents..." />
      ) : documents.length === 0 ? (
        <EmptyState
          title="No documents yet"
          description="Upload a PDF to start researching."
        />
      ) : (
        <DocumentList
          documents={documents}
          onRetry={retry}
          onDelete={handleDelete}
          retryingId={retryingId}
          deletingId={deletingId}
        />
      )}
    </div>
  );
}
