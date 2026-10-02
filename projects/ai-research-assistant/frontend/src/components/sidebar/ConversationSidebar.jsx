/**
 * ConversationSidebar component.
 *
 * Renders chronological list of user research conversations with
 * actions for starting new chats, switching active chats, and deletion.
 */

export default function ConversationSidebar({
  conversations = [],
  activeConversationId,
  loading = false,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
}) {
  return (
    <aside className="conversation-sidebar">
      <div className="sidebar-header">
        <div>
          <h2>Research Assistant</h2>
        </div>

        <button
          type="button"
          onClick={onNewChat}
        >
          + New Chat
        </button>
      </div>

      <div className="conversation-list">
        {loading && (
          <p className="sidebar-status">
            Loading conversations...
          </p>
        )}

        {!loading &&
          conversations.length === 0 && (
            <p className="sidebar-status">
              No conversations yet.
            </p>
          )}

        {conversations.map(
          (conversation) => {
            const active =
              conversation.id ===
              activeConversationId;

            return (
              <div
                key={conversation.id}
                className={`conversation-item ${
                  active ? "active" : ""
                }`}
              >
                <button
                  type="button"
                  className="conversation-select"
                  onClick={() =>
                    onSelectConversation(
                      conversation.id
                    )
                  }
                >
                  <span>
                    {conversation.title ||
                      "Untitled conversation"}
                  </span>
                </button>

                <button
                  type="button"
                  className="conversation-delete"
                  onClick={() =>
                    onDeleteConversation(
                      conversation.id
                    )
                  }
                  aria-label="Delete conversation"
                >
                  ×
                </button>
              </div>
            );
          }
        )}
      </div>
    </aside>
  );
}
