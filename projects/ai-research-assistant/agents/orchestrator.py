import concurrent.futures
from observability import timed_call
from agents.research_agent import ResearchAgent
from agents.calculator_agent import CalculatorAgent
from agents.reasoning_agent import ReasoningAgent


class Orchestrator:

    def __init__(self):
        self.research = ResearchAgent()
        self.calculator = CalculatorAgent()
        self.reasoner = ReasoningAgent()

    def plan_tasks(self, query: str):
        query_lower = query.lower()
        needs_calc = any(kw in query_lower for kw in ["calculate", "multiply", "divide", "add", "subtract", "+", "*", "/"])
        needs_research = any(kw in query_lower for kw in ["paper", "document", "methodology", "dataset", "search", "upload", "according to"])

        # Default fallback: if neither explicitly keyword-matched, run research + LLM reasoning
        if not needs_calc and not needs_research:
            needs_research = True

        return {
            "needs_research": needs_research,
            "needs_calc": needs_calc
        }

    def run(self, query: str, calc_args=None, trace=None):
        plan = self.plan_tasks(query)

        futures = {}
        agent_results = {
            "query": query,
            "research": [],
            "calculator": None
        }

        # Step 8: Parallel Execution using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            if plan["needs_research"]:
                f_res = executor.submit(timed_call, self.research.run, query)
                futures["research"] = f_res

            if plan["needs_calc"] and calc_args:
                f_calc = executor.submit(timed_call, self.calculator.run, calc_args)
                futures["calc"] = f_calc

            # Collect results & observability timings
            if "research" in futures:
                res_output, res_ms = futures["research"].result()
                agent_results["research"] = res_output
                if trace is not None and hasattr(trace, "steps"):
                    trace.steps.append({
                        "step": len(trace.steps) + 1,
                        "agent": self.research.name,
                        "latency_ms": res_ms,
                        "result_count": len(res_output) if isinstance(res_output, list) else 1
                    })

            if "calc" in futures:
                calc_output, calc_ms = futures["calc"].result()
                agent_results["calculator"] = calc_output
                if trace is not None and hasattr(trace, "steps"):
                    trace.steps.append({
                        "step": len(trace.steps) + 1,
                        "agent": self.calculator.name,
                        "latency_ms": calc_ms,
                        "result": calc_output
                    })

        # Step 9: Reasoning Agent synthesizes results
        reason_output, reason_ms = timed_call(self.reasoner.run, agent_results)

        if trace is not None and hasattr(trace, "steps"):
            trace.steps.append({
                "step": len(trace.steps) + 1,
                "agent": self.reasoner.name,
                "latency_ms": reason_ms,
                "output": "Final Synthesis Completed"
            })

        return reason_output
