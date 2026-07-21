class ConversationMemory:

    def __init__(self, max_turns=5):
        self.history = []
        self.max_turns = max_turns

    def add(self, user, assistant):

        self.history.append({
            "user": user,
            "assistant": assistant
        })

        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def context(self):

        conversation = ""

        for turn in self.history:

            conversation += (
                f"User: {turn['user']}\n"
                f"Assistant: {turn['assistant']}\n\n"
            )

        return conversation
