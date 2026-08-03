from agents.base_agent import BaseAgent
from tools import document_search


class ResearchAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Research Agent")

    def run(self, query: str):
        return document_search(query)
