import SourceList from "../sources/SourceList";

function formatContent(content) {
  if (typeof content !== "string") return content;
  const parts = content.split(/(\[S\d+\])/g);
  if (parts.length === 1) return content;
  return parts.map((part, index) =>
    /^\[S\d+\]$/.test(part) ? (
      <span key={index} className="source-reference">
        {part}
      </span>
    ) : (
      part
    )
  );
}

export default function MessageBubble({
  message,
}) {
  const isUser =
    message.role === "user";

  return (
    <div
      className={`message-row ${
        isUser ? "user" : "assistant"
      }`}
    >
      <div className="message-content-wrapper">
        <div className="message-bubble">
          <div className="message-content">
            {formatContent(message.content)}
          </div>
        </div>

        {!isUser &&
          message.sources?.length > 0 && (
            <SourceList
              sources={message.sources}
            />
          )}
      </div>
    </div>
  );
}
