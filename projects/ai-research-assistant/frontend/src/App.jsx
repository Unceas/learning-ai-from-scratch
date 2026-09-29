import ChatWindow from "./components/chat/ChatWindow";
import ChatInput from "./components/chat/ChatInput";
import { useChat } from "./hooks/useChat";

function App() {
  const {
    messages,
    loading,
    error,
    send,
    newChat,
  } = useChat();

  return (
    <main className="app">
      <header className="app-header">
        <div>
          <h1>AI Research Assistant</h1>
          <p>
            Ask questions across your research
            documents.
          </p>
        </div>

        <button
          type="button"
          onClick={newChat}
        >
          New Chat
        </button>
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
    </main>
  );
}

export default App;
