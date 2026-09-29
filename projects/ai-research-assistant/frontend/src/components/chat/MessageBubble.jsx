export default function MessageBubble({
  message,
}) {
  const isUser = message.role === "user";

  return (
    <div
      className={`message-row ${
        isUser ? "user" : "assistant"
      }`}
    >
      <div className="message-bubble">
        <div className="message-content">
          {message.content}
        </div>

        {message.sources?.length > 0 && (
          <div className="message-sources">
            {message.sources.map((source, index) => (
              <span
                key={source.id || `${source.document_id}-${source.chunk_index}-${index}`}
                className="source-reference"
              >
                [{source.id || "S?"}]
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
