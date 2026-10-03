/**
 * ChatContext.
 *
 * Provides shared conversational state across routes, preventing active chat
 * state from resetting when users navigate between /chat and /documents.
 */

import { createContext, useContext } from "react";
import { useChat } from "../hooks/useChat";

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const chat = useChat();

  return (
    <ChatContext.Provider value={chat}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);

  if (!context) {
    throw new Error("useChatContext must be used inside ChatProvider");
  }

  return context;
}
