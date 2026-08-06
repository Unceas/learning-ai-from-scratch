from reflection.critic import review_answer
from reflection.reviser import revise_answer
from reflection.validator import validate_review

MAX_REVISIONS = 2


def run_reflection_loop(question: str, context: str, initial_answer: str, trace=None, max_revisions: int = MAX_REVISIONS):
    current_answer = initial_answer

    reflection_record = {
        "iterations": 0,
        "scores": [],
        "approved": False,
        "history": []
    }

    for i in range(max_revisions + 1):
        reflection_record["iterations"] = i + 1

        review = review_answer(question, context, current_answer)
        score = review.get("score", 10)
        is_approved = review.get("approved", True)
        feedback = review.get("feedback", "")

        reflection_record["scores"].append(score)
        reflection_record["history"].append({
            "iteration": i + 1,
            "score": score,
            "approved": is_approved,
            "feedback": feedback,
            "answer": current_answer
        })

        if is_approved or i == max_revisions:
            reflection_record["approved"] = is_approved
            break

        current_answer = revise_answer(question, context, current_answer, feedback)

    if trace is not None and hasattr(trace, "reflection"):
        trace.reflection = reflection_record

    return current_answer, reflection_record
