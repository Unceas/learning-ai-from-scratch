import ConversationSidebar from "../components/sidebar/ConversationSidebar";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import { useChat } from "../hooks/useChat";

export default function Chat() {
  const {
    messages,
    conversationId,
    conversations,

    loading,
    conversationsLoading,
    error,

    send,
    loadConversation,
    newChat,
    removeConversation,
  } = useChat();

  return (
    <div className="chat-page">
      <ConversationSidebar
        conversations={conversations}
        activeConversationId={conversationId}
        loading={conversationsLoading}
        onNewChat={newChat}
        onSelectConversation={loadConversation}
        onDeleteConversation={removeConversation}
      />

      <section className="chat-main">
        <header className="chat-header">
          <div>
            <h1>AI Research Assistant</h1>
            <p>Ask questions across your research documents.</p>
          </div>
        </header>

        <ChatWindow
          messages={messages}
          loading={loading}
        />

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <ChatInput
          onSend={send}
          disabled={loading}
        />
      </section>
    </div>
  );
}
