import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getConversations,
  getConversation,
  deleteConversation,
} from "../api/conversations";

import { sendMessage } from "../api/chat";
import { normalizeSource } from "../utils/sources";

function generateId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return String(Date.now()) + "-" + Math.random().toString(36).slice(2, 9);
}

function createUserMessage(content) {
  return {
    id: generateId(),
    role: "user",
    content,
    sources: [],
  };
}

function createAssistantMessage(data) {
  return {
    id: generateId(),
    role: "assistant",
    content: data?.answer || "",
    sources: (data?.sources || []).map(
      (source, index) => normalizeSource(source, index)
    ),
  };
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);

  const [loading, setLoading] = useState(false);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadConversations = useCallback(async () => {
    setConversationsLoading(true);

    try {
      const data = await getConversations();
      setConversations(data || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load conversations."
      );
    } finally {
      setConversationsLoading(false);
    }
  }, []);

  const loadConversation = useCallback(async (id) => {
    setError(null);
    setLoading(true);

    try {
      const conversation = await getConversation(id);

      setConversationId(conversation.id);

      const loadedMessages = (conversation.messages || []).map(
        (message) => ({
          id: message.id || generateId(),
          role: message.role,
          content: message.content,
          sources: (message.sources || []).map(
            (source, index) => normalizeSource(source, index)
          ),
        })
      );

      setMessages(loadedMessages);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load conversation."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const send = useCallback(
    async (content) => {
      const trimmed = content.trim();

      if (!trimmed || loading) {
        return;
      }

      setError(null);

      const userMessage = createUserMessage(trimmed);

      setMessages((current) => [
        ...current,
        userMessage,
      ]);

      setLoading(true);

      try {
        const response = await sendMessage(
          trimmed,
          conversationId
        );

        if (response && response.conversation_id) {
          setConversationId(response.conversation_id);
        }

        const assistantMessage = createAssistantMessage(response);

        setMessages((current) => [
          ...current,
          assistantMessage,
        ]);

        // Refresh sidebar because a new conversation/message
        // may have changed its title/order.
        await loadConversations();
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to send message."
        );
      } finally {
        setLoading(false);
      }
    },
    [conversationId, loading, loadConversations]
  );

  const newChat = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setError(null);
  }, []);

  const removeConversation = useCallback(
    async (id) => {
      setError(null);

      try {
        await deleteConversation(id);

        setConversations((current) =>
          current.filter((conversation) => conversation.id !== id)
        );

        if (conversationId === id) {
          setConversationId(null);
          setMessages([]);
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to delete conversation."
        );
      }
    },
    [conversationId]
  );

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return {
    messages,
    conversationId,
    conversations,

    loading,
    conversationsLoading,
    error,

    send,
    loadConversation,
    loadConversations,
    newChat,
    removeConversation,
  };
}
