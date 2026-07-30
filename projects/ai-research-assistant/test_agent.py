from agent import run_agent


queries = [
    "What is 347 multiplied by 29?",
    "Calculate 144 divided by 12.",
    "Explain what retrieval augmented generation means."
]


for query in queries:

    print("\nUSER:")
    print(query)

    print("\nASSISTANT:")
    print(run_agent(query))
