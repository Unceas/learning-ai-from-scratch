TOOL_SCHEMAS = [
    {
        "name": "calculator",
        "description": "Perform basic arithmetic calculations.",
        "parameters": {
            "a": "number",
            "b": "number",
            "operation": [
                "add",
                "subtract",
                "multiply",
                "divide"
            ]
        }
    },

    {
        "name": "document_search",
        "description": (
            "Search uploaded research documents "
            "for information relevant to a query."
        ),
        "parameters": {
            "query": "string"
        }
    }
]
