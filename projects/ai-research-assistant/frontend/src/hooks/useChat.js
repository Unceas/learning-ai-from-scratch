import { useCallback, useState } from "react";
import {
  getConversations,
  getConversation,
} from "../api/conversations";
import { sendMessage } from "../api/chat";

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
    sources: data?.sources || [],
  };
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const send = useCallback(
    async (content) => {
      const trimmed = content.trim();

      if (!trimmed || loading) {
        return;
      }

      setError(null);

      const userMessage = createUserMessage(trimmed);

      // Optimistic UI update
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
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong."
        );
      } finally {
        setLoading(false);
      }
    },
    [conversationId, loading]
  );

  const loadConversation = useCallback(
    async (id) => {
      setError(null);
      setLoading(true);

      try {
        const conversation = await getConversation(id);

        setConversationId(conversation.id);

        setMessages(
          (conversation.messages || []).map((message) => ({
            id: message.id || generateId(),
            role: message.role,
            content: message.content,
            sources: message.sources || [],
          }))
        );
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load conversation."
        );
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load conversations."
      );
    }
  }, []);

  const newChat = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    conversationId,
    conversations,
    loading,
    error,

    send,
    loadConversation,
    loadConversations,
    newChat,
  };
}
