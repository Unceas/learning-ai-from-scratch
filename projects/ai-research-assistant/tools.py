"""Modular tools definitions for assistant function execution."""


def calculator(a: float, b: float, operation: str):

    if operation == "add":
        return a + b

    if operation == "subtract":
        return a - b

    if operation == "multiply":
        return a * b

    if operation == "divide":

        if b == 0:
            return "Division by zero is not allowed."

        return a / b

    return "Unsupported operation."


TOOLS = {
    "calculator": calculator
}
