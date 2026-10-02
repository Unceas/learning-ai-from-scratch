import { useState } from "react";
import Chat from "./pages/Chat";
import Documents from "./pages/Documents";

export default function App() {
  const [page, setPage] = useState("chat");

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <button
          type="button"
          className={page === "chat" ? "active" : ""}
          onClick={() => setPage("chat")}
        >
          Chat
        </button>

        <button
          type="button"
          className={page === "documents" ? "active" : ""}
          onClick={() => setPage("documents")}
        >
          Documents
        </button>
      </nav>

      {page === "chat" && <Chat />}
      {page === "documents" && <Documents />}
    </div>
  );
}
