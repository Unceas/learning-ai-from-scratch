import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import EmptyState from "../common/EmptyState";

export default function ChatWindow({
  messages = [],
  sending = false,
  loading = false,
  onRetry,
  selectedSource,
  onSourceClick,
}) {
  const bottomRef = useRef(null);
  const isWaiting = sending || loading;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isWaiting]);

  return (
    <section className="chat-window">
      {messages.length === 0 && !isWaiting ? (
        <EmptyState
          title="Start your research"
          description="Ask a question about the documents you've uploaded."
        />
      ) : (
        messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onRetry={onRetry}
            selectedSource={selectedSource}
            onSourceClick={onSourceClick}
          />
        ))
      )}

      {isWaiting && <TypingIndicator />}

      <div ref={bottomRef} />
    </section>
  );
}
