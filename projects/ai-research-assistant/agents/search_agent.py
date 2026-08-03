from agents.research_agent import ResearchAgent

class SearchAgent(ResearchAgent):
    """Search Agent specializing in search queries across indexed knowledge."""
    def __init__(self):
        super().__init__()
        self.name = "Search Agent"
