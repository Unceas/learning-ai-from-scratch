import { Profiler, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ConversationSidebar from "../components/sidebar/ConversationSidebar";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import LoadingState from "../components/common/LoadingState";
import SourcePreview from "../components/sources/SourcePreview";
import { useChatContext } from "../context/ChatContext";

export default function Chat() {
  const navigate = useNavigate();
  const { conversationId: routeParam } = useParams();
  const [selectedSource, setSelectedSource] = useState(null);

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

  function handleSourceClick(source) {
    const sourceObj = typeof source === "object" && source !== null ? source : { id: source };
    setSelectedSource(sourceObj);

    const sourceId = sourceObj?.id || source;
    if (sourceId && typeof requestAnimationFrame !== "undefined") {
      requestAnimationFrame(() => {
        const element = document.getElementById(`source-${sourceId}`);
        element?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      });
    }
  }

  function onChatRender(id, phase, actualDuration, baseDuration) {
    if (import.meta.env?.DEV) {
      console.debug({
        id,
        phase,
        actualDuration: Math.round(actualDuration * 100) / 100,
        baseDuration: Math.round(baseDuration * 100) / 100,
      });
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
            <p>Compare findings, ask follow-up questions, and inspect supporting evidence.</p>
          </div>
        </header>

        <div className="chat-layout-wrapper">
          <div className="chat-content-pane">
            {loadingConversation ? (
              <LoadingState message="Loading conversation..." />
            ) : (
              <Profiler id="ChatMessages" onRender={onChatRender}>
                <ChatWindow
                  messages={messages}
                  sending={sending}
                  onRetry={retryMessage}
                  selectedSource={selectedSource}
                  onSourceClick={handleSourceClick}
                />
              </Profiler>
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
          </div>

          {selectedSource && (
            <SourcePreview
              source={selectedSource}
              onClose={() => setSelectedSource(null)}
            />
          )}
        </div>
      </section>
    </div>
  );
}
