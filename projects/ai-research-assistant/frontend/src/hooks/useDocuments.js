import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getDocuments,
  uploadDocument,
  retryDocument,
  deleteDocument,
} from "../api/documents";
import { getUserError } from "../api/client";
import { getToken } from "../auth/storage";

const POLL_INTERVAL = 2500;
const MAX_PROCESSING_TIME = 5 * 60 * 1000; // 5 minutes

export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [retryingId, setRetryingId] = useState(null);
  const [pollingTimedOut, setPollingTimedOut] = useState(false);

  const pollingStartedAt = useRef(null);

  const fetchDocuments = useCallback(async (showLoading = true) => {
    if (!getToken()) {
      setDocuments([]);
      setLoading(false);
      return;
    }

    if (showLoading) {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await getDocuments();
      const items = Array.isArray(data) ? data : (data?.documents || []);
      setDocuments(items);
    } catch (err) {
      setError(getUserError(err));
    } finally {
      if (showLoading) {
        setLoading(false);
      }
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
      await fetchDocuments(false);
      return result;
    } catch (err) {
      const message = getUserError(err);
      setError(message);
      throw err;
    } finally {
      setUploading(false);
    }
  }, [fetchDocuments]);

  const retry = useCallback(async (id) => {
    if (!id) return;

    setRetryingId(id);
    setError(null);

    try {
      await retryDocument(id);
      await fetchDocuments(false);
    } catch (err) {
      setError(getUserError(err));
    } finally {
      setRetryingId(null);
    }
  }, [fetchDocuments]);

  const remove = useCallback(async (id) => {
    if (!id) return;

    setDeletingId(id);
    setError(null);

    try {
      await deleteDocument(id);
      setDocuments((current) =>
        current.filter((document) => document.id !== id)
      );
    } catch (err) {
      setError(getUserError(err));
    } finally {
      setDeletingId(null);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchDocuments(true);
  }, [fetchDocuments]);

  // Conditional polling for processing documents with timeout ceiling
  useEffect(() => {
    const hasProcessing = documents.some(
      (document) => document.status === "processing"
    );

    if (!hasProcessing) {
      pollingStartedAt.current = null;
      setPollingTimedOut(false);
      return;
    }

    if (!pollingStartedAt.current) {
      pollingStartedAt.current = Date.now();
    }

    if (Date.now() - pollingStartedAt.current > MAX_PROCESSING_TIME) {
      setPollingTimedOut(true);
      return;
    }

    const interval = setInterval(() => {
      if (Date.now() - pollingStartedAt.current > MAX_PROCESSING_TIME) {
        setPollingTimedOut(true);
        clearInterval(interval);
        return;
      }

      fetchDocuments(false);
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [documents, fetchDocuments]);

  // Clean up state on session logout / token expiry
  useEffect(() => {
    function handleLogoutOrExpiry() {
      setDocuments([]);
      setLoading(false);
      pollingStartedAt.current = null;
      setPollingTimedOut(false);
    }

    if (typeof window !== "undefined") {
      window.addEventListener("auth:expired", handleLogoutOrExpiry);
      return () => {
        window.removeEventListener("auth:expired", handleLogoutOrExpiry);
      };
    }
  }, []);

  return {
    documents,
    loading,
    uploading,
    error,
    deletingId,
    retryingId,
    pollingTimedOut,
    fetchDocuments,
    fetchDocs: fetchDocuments,
    upload,
    retry,
    remove,
  };
}

export default useDocuments;
