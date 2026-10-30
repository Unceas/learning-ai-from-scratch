/**
 * MessageBubble component.
 *
 * Distinguishes user messages (with optimistic pending/failed states)
 * and assistant responses (with rich Markdown rendering and interactive source attribution).
 */

import { memo } from "react";
import MarkdownAnswer from "./MarkdownAnswer";
import SourceList from "../sources/SourceList";
import FailedMessage from "./FailedMessage";
import AnswerFeedback from "./AnswerFeedback";

function MessageBubble({
  message,
  onRetry,
  selectedSource,
  onSourceClick,
}) {
  const isUser = message.role === "user";
  const statusClass = message.status ? `message-${message.status}` : "";

  return (
    <div
      className={`message-row ${
        isUser ? "user" : "assistant"
      }`}
    >
      <div className="message-content-wrapper">
        <div className={`message-bubble ${statusClass}`}>
          <div className="message-content">
            {isUser ? (
              <div className="plain-message">
                {message.content}
              </div>
            ) : (
              <MarkdownAnswer
                content={message.content}
                sources={message.sources || []}
                onSourceClick={onSourceClick}
              />
            )}
          </div>
        </div>

        {isUser && message.status === "failed" && (
          <FailedMessage
            onRetry={() => onRetry && onRetry(message)}
          />
        )}

        {!isUser && message.sources?.length > 0 && (
          <SourceList
            sources={message.sources}
            selectedSource={selectedSource}
            onSourceClick={onSourceClick}
          />
        )}

        {!isUser && Number.isInteger(Number(message.id)) && Number(message.id) > 0 && (
          <AnswerFeedback messageId={Number(message.id)} />
        )}
      </div>
    </div>
  );
}

export default memo(MessageBubble);
