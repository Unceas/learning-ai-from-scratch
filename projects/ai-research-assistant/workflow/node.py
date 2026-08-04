from tools import document_search, calculator
from llm import generate_answer


class Node:

    def run(self, state):
        raise NotImplementedError


class ResearchNode(Node):

    def run(self, state):
        if state.query:
            state.context = document_search(state.query)
        return state


class CalculatorNode(Node):

    def run(self, state):
        if "calculation" in state.metadata:
            state.tool_results["calculator"] = calculator(
                **state.metadata["calculation"]
            )
        return state


class ReasoningNode(Node):

    def run(self, state):
        contexts = state.context if state.context else []
        if state.tool_results.get("calculator") is not None:
            calc_text = f"Calculator Result: {state.tool_results['calculator']}"
            contexts = contexts + [{"text": calc_text, "document": "Calculator", "page": 1, "chunk": 0}]

        answer_tokens = []
        for token in generate_answer(state.query, contexts):
            answer_tokens.append(token)

        state.answer = "".join(answer_tokens)
        return state
