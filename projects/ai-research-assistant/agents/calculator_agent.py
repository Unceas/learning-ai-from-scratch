from agents.base_agent import BaseAgent
from tools import calculator


class CalculatorAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Calculator Agent")

    def run(self, task):
        if isinstance(task, dict):
            return calculator(
                a=task.get("a", 0),
                b=task.get("b", 0),
                operation=task.get("operation", "add")
            )
        
        # If passed positional or keyword args tuple/dict
        if isinstance(task, (list, tuple)) and len(task) >= 3:
            return calculator(a=task[0], b=task[1], operation=task[2])

        return "Calculator agent requires a valid task parameter dictionary or tuple."
