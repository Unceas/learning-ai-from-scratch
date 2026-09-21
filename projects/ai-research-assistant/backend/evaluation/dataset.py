"""Evaluation dataset for benchmarking RAG retrieval, citations, and answer generation."""

from typing import Any, Dict, List

EVAL_DATASET: List[Dict[str, Any]] = [
    {
        "question": "What architecture does the paper propose?",
        "expected_documents": ["attention.pdf"],
        "expected_topics": ["Transformer", "self-attention", "encoder-decoder"],
        "type": "semantic",
    },
    {
        "question": "What is the purpose of self-attention?",
        "expected_documents": ["attention.pdf"],
        "expected_topics": ["relating positions", "representations of sequence"],
        "type": "semantic",
    },
    {
        "question": "How does the Transformer encoder process tokens?",
        "expected_documents": ["attention.pdf"],
        "expected_topics": ["feed-forward", "multi-head attention", "layer normalization"],
        "type": "semantic",
    },
    {
        "question": "Which dataset was used for the experiment?",
        "expected_documents": ["experiment.pdf"],
        "expected_topics": ["WMT 2014", "English-to-German", "benchmark"],
        "type": "factual",
    },
    {
        "question": "Which learning rate schedule was used during training?",
        "expected_documents": ["experiment.pdf"],
        "expected_topics": ["warmup steps", "decay", "Adam optimizer"],
        "type": "factual",
    },
    {
        "question": "Which hardware was used to evaluate model performance?",
        "expected_documents": ["experiment.pdf"],
        "expected_topics": ["GPUs", "TPU chips", "training time"],
        "type": "factual",
    },
    {
        "question": "At what temperature do superconducting qubits operate?",
        "expected_documents": ["quantum.pdf"],
        "expected_topics": ["millikelvin", "cryogenic temperatures"],
        "type": "factual",
    },
    {
        "question": "What principles govern quantum superposition?",
        "expected_documents": ["quantum.pdf"],
        "expected_topics": ["qubits", "linear combination", "quantum states"],
        "type": "semantic",
    },
    {
        "question": "How does quantum error correction protect logical qubits?",
        "expected_documents": ["quantum.pdf"],
        "expected_topics": ["surface codes", "entanglement", "decoherence"],
        "type": "semantic",
    },
    {
        "question": "What are the primary sources of carbon emissions identified in the report?",
        "expected_documents": ["climate_report.pdf"],
        "expected_topics": ["fossil fuels", "transportation", "energy generation"],
        "type": "semantic",
    },
    {
        "question": "How many percentage reduction targets are proposed for 2030?",
        "expected_documents": ["climate_report.pdf"],
        "expected_topics": ["emissions reduction", "baseline percentage", "net zero goals"],
        "type": "factual",
    },
    {
        "question": "How does dense vector search differ from keyword retrieval?",
        "expected_documents": ["neural_search.pdf"],
        "expected_topics": ["semantic similarity", "embeddings", "exact overlap"],
        "type": "comparison",
    },
    {
        "question": "Compare cross-encoder re-ranking versus bi-encoder search metrics.",
        "expected_documents": ["neural_search.pdf"],
        "expected_topics": ["MRR", "NDCG", "precision at k"],
        "type": "comparison",
    },
    {
        "question": "Why is document deduplication critical in ingestion pipelines?",
        "expected_documents": ["neural_search.pdf"],
        "expected_topics": ["storage efficiency", "vector store pollution", "hash collisions"],
        "type": "semantic",
    },
    {
        "question": "Compare multi-head attention versus single-head representation learning.",
        "expected_documents": ["attention.pdf"],
        "expected_topics": ["jointly attend to information", "different representation subspaces"],
        "type": "comparison",
    },
]
