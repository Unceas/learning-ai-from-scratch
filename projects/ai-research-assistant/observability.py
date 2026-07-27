import json
import time
from dataclasses import dataclass, field


@dataclass
class RAGTrace:
    query: str

    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    generation_ms: float = 0.0
    ttft_ms: float = 0.0

    retrieved_count: int = 0
    final_context_count: int = 0
    streamed: bool = True
    tokens_generated: int = 0

    sources: list = field(default_factory=list)

    @property
    def total_ms(self):
        return (
            self.retrieval_ms
            + self.reranking_ms
            + self.generation_ms
        )


def timed_call(function, *args, **kwargs):

    start = time.perf_counter()

    result = function(
        *args,
        **kwargs
    )

    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000

    return result, elapsed_ms


def save_trace(trace, path="rag_traces.jsonl"):

    record = {
        "query": trace.query,
        "retrieval_ms": trace.retrieval_ms,
        "reranking_ms": trace.reranking_ms,
        "generation_ms": trace.generation_ms,
        "ttft_ms": trace.ttft_ms,
        "total_ms": trace.total_ms,
        "retrieved_count": trace.retrieved_count,
        "final_context_count": trace.final_context_count,
        "streamed": trace.streamed,
        "tokens_generated": trace.tokens_generated,
        "sources": trace.sources
    }

    with open(path, "a", encoding="utf-8") as file:
        file.write(
            json.dumps(record) + "\n"
        )
