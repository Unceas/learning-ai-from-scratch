from workflow import WorkflowState, ResearchNode, CalculatorNode, ReasoningNode, Workflow, StateGraph

print("--- Testing Sequential Workflow Engine ---")
wf = Workflow()
wf.add_node(ResearchNode())
wf.add_node(CalculatorNode())
wf.add_node(ReasoningNode())

state = WorkflowState()
state.query = "What methodology does the paper use?"
state.metadata = {"calculation": {"a": 144, "b": 12, "operation": "divide"}}

result_state = wf.execute(state)
print("Context Chunks Retrieved:", len(result_state.context) if result_state.context else 0)
print("Tool Results:", result_state.tool_results)
print("Final Answer Generated:", bool(result_state.answer))
assert result_state.answer is not None

print("\n--- Testing StateGraph ---")
graph = StateGraph()
graph.add_node("research", ResearchNode())
graph.add_node("reasoning", ReasoningNode())

graph.set_entry_point("research")
graph.add_edge("research", "reasoning")

graph_state = WorkflowState()
graph_state.query = "Summarize the key findings."

final_graph_state = graph.execute(graph_state)
print("Graph Execution Answer Generated:", bool(final_graph_state.answer))
assert final_graph_state.answer is not None
print("\n[Success] Workflow Engine Verified Successfully!")
