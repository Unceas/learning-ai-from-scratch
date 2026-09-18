"""Automated test suite for Day 143: RAG Evaluation Framework."""

import os
from backend.evaluation.dataset import EVAL_DATASET
from backend.evaluation.retrieval_metrics import recall_at_k, mean_recall
from backend.evaluation.generation_metrics import citation_precision, validate_citations, evaluate_grounding
from backend.evaluation.run import run_evaluation


def test_dataset_structure():
    print("--- 1. Testing Evaluation Dataset Structure ---")
    assert len(EVAL_DATASET) >= 10, f"Expected at least 10 evaluation questions, got {len(EVAL_DATASET)}"
    for idx, item in enumerate(EVAL_DATASET, 1):
        assert "question" in item and item["question"].strip(), f"Item {idx} missing valid question"
        assert "expected_documents" in item and len(item["expected_documents"]) >= 1, f"Item {idx} missing expected_documents"
        for doc in item["expected_documents"]:
            assert isinstance(doc, str) and doc.endswith(".pdf"), f"Expected .pdf document in item {idx}, got {doc}"
    print(f"Dataset verified successfully ({len(EVAL_DATASET)} questions).")


def test_retrieval_metrics():
    print("\n--- 2. Testing Recall@K and Mean Recall ---")
    # Perfect top-1 hit
    retrieved = ["attention.pdf", "survey.pdf", "notes.pdf"]
    expected = ["attention.pdf"]
    assert recall_at_k(retrieved, expected, k=1) == 1.0
    assert recall_at_k(retrieved, expected, k=3) == 1.0

    # Hit at rank 3
    retrieved_3 = ["other1.pdf", "other2.pdf", "attention.pdf", "other3.pdf"]
    assert recall_at_k(retrieved_3, expected, k=2) == 0.0
    assert recall_at_k(retrieved_3, expected, k=3) == 1.0

    # Multi-document partial recall
    multi_expected = ["doc_a.pdf", "doc_b.pdf"]
    assert recall_at_k(["doc_a.pdf", "other.pdf"], multi_expected, k=2) == 0.5
    assert recall_at_k(["doc_a.pdf", "doc_b.pdf"], multi_expected, k=2) == 1.0

    # Edge cases
    assert recall_at_k([], expected, k=5) == 0.0
    assert recall_at_k(retrieved, [], k=5) == 0.0
    assert recall_at_k(retrieved, expected, k=0) == 0.0

    # Mean recall aggregation
    scores = [1.0, 1.0, 0.0, 1.0]
    assert mean_recall(scores) == 0.75
    assert mean_recall([]) == 0.0
    print("Retrieval recall metrics passed.")


def test_citation_metrics():
    print("\n--- 3. Testing Citation Precision and Validation ---")
    valid_sources = {"S1", "S2", "S3"}

    # 1. Fully valid citations
    ans_valid = "The Transformer uses self-attention [S1] and feed-forward layers [S2]."
    assert citation_precision(ans_valid, valid_sources) == 1.0
    val_res = validate_citations(ans_valid, valid_sources)
    assert val_res["valid"] == ["[S1]", "[S2]"]
    assert val_res["invalid"] == []

    # 2. Mixed valid & hallucinated citations (2 valid / 3 total = 0.67)
    ans_mixed = "The model uses self-attention [S1], processes in parallel [S2], and scales [S7]."
    prec = citation_precision(ans_mixed, valid_sources)
    assert round(prec, 2) == 0.67
    val_mixed = validate_citations(ans_mixed, valid_sources)
    assert val_mixed["valid"] == ["[S1]", "[S2]"]
    assert val_mixed["invalid"] == ["[S7]"]

    # 3. All invalid citations
    ans_bad = "Unsupported claim without real evidence [S99]."
    assert citation_precision(ans_bad, valid_sources) == 0.0
    val_bad = validate_citations(ans_bad, valid_sources)
    assert val_bad["valid"] == []
    assert val_bad["invalid"] == ["[S99]"]

    # 4. No citations generated
    ans_none = "Direct answer without citations."
    assert citation_precision(ans_none, valid_sources) == 1.0
    print("Citation precision and validation metrics passed.")


def test_grounding_evaluation():
    print("\n--- 4. Testing Answer Grounding Evaluation ---")
    context = (
        "[S1]\nFile: experiment.pdf\nChunk: 0\n\n"
        "The experiment used the CIFAR-10 dataset and achieved 92 percent test accuracy."
    )

    # 1. Supported answer
    supported_ans = "The experiment evaluated on the CIFAR-10 dataset achieving 92 percent accuracy. [S1]"
    res_sup = evaluate_grounding(context, supported_ans)
    assert res_sup == "SUPPORTED"

    # 2. Unsupported / Hallucinated answer
    hallucinated_ans = "The experiment evaluated on ImageNet with superconducting cryogenic quantum qubits."
    res_unsup = evaluate_grounding(context, hallucinated_ans)
    assert res_unsup == "UNSUPPORTED"

    # 3. Clean fallback when zero context
    fallback_ans = "I couldn't find enough information in the indexed documents."
    assert evaluate_grounding("", fallback_ans) == "SUPPORTED"
    print("Answer grounding evaluation passed.")


def test_evaluation_runner_small_subset():
    print("\n--- 5. Testing Evaluation Runner Execution ---")
    mini_dataset = EVAL_DATASET[:2]
    eval_res = run_evaluation(
        dataset=mini_dataset,
        user_id="test_runner_user",
        baseline_output_path="backend/evaluation/test_baseline.json"
    )

    assert eval_res["questions_count"] == 2
    assert "retrieval" in eval_res
    assert "recall_at_3" in eval_res["retrieval"]
    assert "recall_at_5" in eval_res["retrieval"]
    assert 0.0 <= eval_res["retrieval"]["recall_at_3"] <= 1.0
    assert 0.0 <= eval_res["retrieval"]["recall_at_5"] <= 1.0
    assert "citations" in eval_res
    assert 0.0 <= eval_res["citations"]["citation_validity"] <= 1.0
    assert "generation" in eval_res
    assert 0.0 <= eval_res["generation"]["grounded_answers"] <= 1.0
    if os.path.exists("backend/evaluation/test_baseline.json"):
        os.remove("backend/evaluation/test_baseline.json")
    print("Evaluation runner execution and baseline saving passed.")


def main():
    test_dataset_structure()
    test_retrieval_metrics()
    test_citation_metrics()
    test_grounding_evaluation()
    test_evaluation_runner_small_subset()
    print("\n[Success] Day 143 RAG Evaluation Framework Verified Successfully!")


if __name__ == "__main__":
    main()
