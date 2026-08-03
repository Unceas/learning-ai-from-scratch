from agents import Orchestrator

orchestrator = Orchestrator()

queries = [
    "Summarize the uploaded paper methodology.",
    "Calculate 347 multiplied by 29.",
    "Summarize the uploaded paper and calculate 144 divided by 12."
]

for query in queries:
    print("\n--------------------------------------------------")
    print(f"USER QUERY: {query}")
    print("--------------------------------------------------")

    calc_args = {"a": 347, "b": 29, "operation": "multiply"} if "347" in query else (
        {"a": 144, "b": 12, "operation": "divide"} if "144" in query else None
    )

    response = orchestrator.run(query, calc_args=calc_args)
    print("ORCHESTRATOR RESPONSE:")
    print(response)
