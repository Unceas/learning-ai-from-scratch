import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getDocuments,
  getDocumentStatus,
  uploadDocument,
  retryDocument,
  deleteDocument,
} from "../api/documents";

const POLL_INTERVAL = 2500;

export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getDocuments();
      const items = Array.isArray(data) ? data : (data?.documents || []);
      setDocuments(items);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load documents."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const upload = useCallback(async (file) => {
    if (!file) {
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const result = await uploadDocument(file);
      await fetchDocs();
      return result;
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Upload failed."
      );
      throw err;
    } finally {
      setUploading(false);
    }
  }, [fetchDocs]);

  const retry = useCallback(async (id) => {
    setError(null);

    try {
      await retryDocument(id);
      await fetchDocs();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Retry failed."
      );
    }
  }, [fetchDocs]);

  const remove = useCallback(async (id) => {
    setError(null);

    try {
      await deleteDocument(id);
      setDocuments((current) =>
        current.filter((document) => document.id !== id)
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to delete document."
      );
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Recursive polling for documents in 'processing' state
  useEffect(() => {
    let cancelled = false;
    let timeoutId;

    async function poll() {
      const processingDocuments = documents.filter(
        (document) => document.status === "processing"
      );

      if (cancelled || processingDocuments.length === 0) {
        return;
      }

      for (const document of processingDocuments) {
        try {
          const updated = await getDocumentStatus(document.id);

          if (cancelled) {
            return;
          }

          setDocuments((current) =>
            current.map((item) =>
              item.id === updated.id ? updated : item
            )
          );
        } catch (err) {
          console.error(`Polling failed for document ${document.id}`, err);
        }
      }

      if (!cancelled) {
        timeoutId = setTimeout(poll, POLL_INTERVAL);
      }
    }

    poll();

    return () => {
      cancelled = true;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [documents]);

  return {
    documents,
    loading,
    uploading,
    error,
    fetchDocs,
    upload,
    retry,
    remove,
  };
}
