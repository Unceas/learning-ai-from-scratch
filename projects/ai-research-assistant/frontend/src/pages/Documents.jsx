import UploadDocument from "../components/documents/UploadDocument";
import DocumentList from "../components/documents/DocumentList";
import { useDocuments } from "../hooks/useDocuments";

export default function Documents() {
  const {
    documents,
    loading,
    uploading,
    error,
    upload,
    retry,
    remove,
  } = useDocuments();

  return (
    <main className="documents-page">
      <header className="documents-header">
        <h1>Documents</h1>
        <p>Upload research papers and manage indexed documents.</p>
      </header>

      <UploadDocument
        onUpload={upload}
        uploading={uploading}
      />

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {loading ? (
        <p className="loading-state">Loading documents...</p>
      ) : (
        <DocumentList
          documents={documents}
          onRetry={retry}
          onDelete={remove}
        />
      )}
    </main>
  );
}
