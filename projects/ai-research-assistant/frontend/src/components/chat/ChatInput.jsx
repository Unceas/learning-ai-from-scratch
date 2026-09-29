import { useState } from "react";

export default function ChatInput({
  onSend,
  disabled = false,
}) {
  const [value, setValue] = useState("");

  function submit() {
    const message = value.trim();

    if (!message || disabled) {
      return;
    }

    onSend(message);
    setValue("");
  }

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="chat-input">
      <textarea
        value={value}
        onChange={(event) =>
          setValue(event.target.value)
        }
        onKeyDown={handleKeyDown}
        placeholder="Ask a research question..."
        disabled={disabled}
        rows={1}
      />

      <button
        type="button"
        onClick={submit}
        disabled={
          disabled || !value.trim()
        }
      >
        Send
      </button>
    </div>
  );
}
