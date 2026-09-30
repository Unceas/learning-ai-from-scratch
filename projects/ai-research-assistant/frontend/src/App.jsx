import { useState } from "react";
import Documents from "./pages/Documents";
import Chat from "./pages/Chat";

function App() {
  const [page, setPage] = useState("chat");

  return (
    <div className="app-container">
      <nav className="main-nav">
        <button
          type="button"
          className={`nav-btn ${page === "chat" ? "active" : ""}`}
          onClick={() => setPage("chat")}
        >
          Chat
        </button>

        <button
          type="button"
          className={`nav-btn ${page === "documents" ? "active" : ""}`}
          onClick={() => setPage("documents")}
        >
          Documents
        </button>
      </nav>

      <div className="page-content">
        {page === "chat" && <Chat />}
        {page === "documents" && <Documents />}
      </div>
    </div>
  );
}

export default App;
