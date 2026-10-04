import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ConversationSidebar from "../components/sidebar/ConversationSidebar";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import LoadingState from "../components/common/LoadingState";
import { useChatContext } from "../context/ChatContext";

export default function Chat() {
  const navigate = useNavigate();
  const { conversationId: routeParam } = useParams();

  const {
    messages,
    conversationId,
    conversations,
    sending,
    loadingConversation,
    conversationsLoading,
    error,
    send,
    retryMessage,
    loadConversation,
    newChat,
    removeConversation,
  } = useChatContext();

  const activeId = routeParam ? Number(routeParam) : null;

  useEffect(() => {
    if (activeId !== null && !Number.isNaN(activeId)) {
      if (conversationId !== activeId) {
        loadConversation(activeId);
      }
    } else {
      if (conversationId !== null) {
        newChat();
      }
    }
  }, [activeId, conversationId, loadConversation, newChat]);

  async function handleSend(content) {
    const res = await send(content);
    if (!activeId && res?.conversation_id) {
      navigate(`/chat/${res.conversation_id}`, { replace: true });
    }
  }

  function handleConversationSelect(id) {
    navigate(`/chat/${id}`);
  }

  function handleNewChat() {
    newChat();
    navigate("/chat");
  }

  function handleDeleteConversation(id) {
    removeConversation(id);
    if (activeId === id) {
      navigate("/chat");
    }
  }

  return (
    <div className="chat-page">
      <ConversationSidebar
        conversations={conversations}
        activeConversationId={activeId ?? conversationId}
        loading={conversationsLoading}
        onNewChat={handleNewChat}
        onSelectConversation={handleConversationSelect}
        onDeleteConversation={handleDeleteConversation}
      />

      <section className="chat-main">
        <header className="chat-header">
          <div>
            <h1>AI Research Assistant</h1>
            <p>Ask questions across your research documents.</p>
          </div>
        </header>

        {loadingConversation ? (
          <LoadingState message="Loading conversation..." />
        ) : (
          <ChatWindow
            messages={messages}
            sending={sending}
            onRetry={retryMessage}
          />
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <ChatInput
          onSend={handleSend}
          disabled={sending || loadingConversation}
        />
      </section>
    </div>
  );
}
