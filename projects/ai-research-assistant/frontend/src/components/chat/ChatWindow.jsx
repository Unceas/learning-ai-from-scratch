import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

export default function ChatWindow({
  messages,
  loading,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  return (
    <section className="chat-window">
      {messages.length === 0 && !loading ? (
        <div className="empty-chat">
          <h2>Research Assistant</h2>
          <p>
            Ask a question about the documents
            you've uploaded.
          </p>
        </div>
      ) : (
        messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
          />
        ))
      )}

      {loading && <TypingIndicator />}

      <div ref={bottomRef} />
    </section>
  );
}
