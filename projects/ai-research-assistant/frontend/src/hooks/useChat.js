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

import { sendMessage as sendChatMessage } from "../api/chat";
import { getUserError } from "../api/client";
import { normalizeSource } from "../utils/sources";

function generateId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return String(Date.now()) + "-" + Math.random().toString(36).slice(2, 9);
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);

  const [sending, setSending] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadConversations = useCallback(async () => {
    setConversationsLoading(true);

    try {
      const data = await getConversations();
      setConversations(data || []);
    } catch (err) {
      setError(getUserError(err));
    } finally {
      setConversationsLoading(false);
    }
  }, []);

  const loadConversation = useCallback(async (id) => {
    if (!id) return;
    setError(null);
    setLoadingConversation(true);

    try {
      const conversation = await getConversation(id);
      setConversationId(conversation.id);

      const loadedMessages = (conversation.messages || []).map((message) => ({
        id: message.id || generateId(),
        role: message.role,
        content: message.content,
        status: "sent",
        sources: (message.sources || []).map((source, index) =>
          normalizeSource(source, index)
        ),
      }));

      setMessages(loadedMessages);
      return conversation;
    } catch (err) {
      setError(getUserError(err));
    } finally {
      setLoadingConversation(false);
    }
  }, []);

  const send = useCallback(
    async (content) => {
      const trimmed = content?.trim() || "";

      if (!trimmed || sending) {
        return null;
      }

      setError(null);

      const optimisticId = `temp-${Date.now()}`;
      const optimisticMessage = {
        id: optimisticId,
        role: "user",
        content: trimmed,
        status: "pending",
        sources: [],
      };

      setMessages((prev) => [...prev, optimisticMessage]);
      setSending(true);

      try {
        const response = await sendChatMessage(trimmed, conversationId);

        setMessages((prev) => [
          ...prev.map((msg) =>
            msg.id === optimisticId
              ? { ...msg, status: "sent" }
              : msg
          ),
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: response?.answer || "",
            status: "sent",
            sources: (response?.sources || []).map((source, index) =>
              normalizeSource(source, index)
            ),
          },
        ]);

        if (response && response.conversation_id) {
          setConversationId(response.conversation_id);
        }

        await loadConversations();
        return response;
      } catch (err) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === optimisticId
              ? { ...msg, status: "failed" }
              : msg
          )
        );
        setError(getUserError(err));
        return null;
      } finally {
        setSending(false);
      }
    },
    [conversationId, sending, loadConversations]
  );

  const retryMessage = useCallback(
    async (failedMessage) => {
      if (!failedMessage?.content || sending) return null;

      // Remove the failed temporary message before retrying
      setMessages((prev) =>
        prev.filter((msg) => msg.id !== failedMessage.id)
      );

      return await send(failedMessage.content);
    },
    [send, sending]
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
        setError(getUserError(err));
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

    sending,
    loadingConversation,
    conversationsLoading,
    loading: sending || loadingConversation,
    error,

    send,
    sendMessage: send,
    retryMessage,
    loadConversation,
    loadConversations,
    newChat,
    removeConversation,
    deleteConversation: removeConversation,
  };
}

export default useChat;
