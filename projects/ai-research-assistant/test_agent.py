from agent import run_agent


queries = [
    "Calculate 628 multiplied by 37.",

    "What methodology does the uploaded paper use?",

    "According to my document, what dataset was used?",

    "What is retrieval augmented generation?"
]


for query in queries:

    print("\nUSER:", flush=True)
    print(query, flush=True)

    print("\nASSISTANT:", flush=True)
    print(run_agent(query), flush=True)
