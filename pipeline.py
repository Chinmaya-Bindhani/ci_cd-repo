"""
Token optimised agent pipeline with 3 optimisations over naive aproach.
Run: python pipeline.py
"""
import json
from dataclasses import dataclass, field


def count_tokens(text: str) -> int:
    """Aprox token count (~4 chars/token)."""
    return max(1, len(text) // 4)


SYSTEM_PROMPT = """You are a backend engineering assistant. You have access to
tools for searching documentation, running code, and querying a database.
Always validate tool outputs before using them. Never fabricate data.
""" * 40

TOOL_SCHEMAS = [
    {"name": "search_docs", "description": "Search internal docs", "parameters": {}},
    {"name": "run_query", "description": "Run a SQL query", "parameters": {}},
    {"name": "call_api", "description": "Call an internal API", "parameters": {}},
] * 20

FEW_SHOT_EXAMPLES = "Example Q&A pair.\n" * 800


@dataclass
class Turn:
    role: str
    content: str


@dataclass
class NaiveAgent:
    """Baseline: re-sends everything every call."""
    history: list[Turn] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)

    def build_prompt(self, user_input: str) -> str:
        parts = [SYSTEM_PROMPT, json.dumps(TOOL_SCHEMAS), FEW_SHOT_EXAMPLES]
        parts += [t.content for t in self.history]
        parts += self.documents
        parts.append(user_input)
        return "\n".join(parts)


@dataclass
class OptimizedAgent:
    """
    Optimised: static content is cacheable, history compressed with sliding
    window, documents retrieved by relevenace instead of stuffed whole.
    """
    history: list[Turn] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    keep_last: int = 4
    cache_hit: bool = False

    def compress_history(self) -> list[Turn]:
        if len(self.history) <= self.keep_last:
            return self.history
        old, recent = self.history[:-self.keep_last], self.history[-self.keep_last:]
        summary = self._summarize(old)
        return [Turn("system", f"[Summary of earlier steps]: {summary}")] + recent

    @staticmethod
    def _summarize(turns: list[Turn]) -> str:
        joined = " ".join(t.content for t in turns)
        return joined[:200] + ("..." if len(joined) > 200 else "")

    def retrieve_relevant_chunks(self, query: str, top_k: int = 3) -> list[str]:
        """Keyword-overlap retreiver."""
        scored = []
        query_words = set(query.lower().split())
        for doc in self.documents:
            chunks = [doc[i:i + 500] for i in range(0, len(doc), 500)]
            for chunk in chunks:
                overlap = len(query_words & set(chunk.lower().split()))
                scored.append((overlap, chunk))
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:top_k]]

    def build_prompt(self, user_input: str) -> tuple[str, int]:
        """Returns (prompt, effective_billed_tokens)."""
        static_block = SYSTEM_PROMPT + json.dumps(TOOL_SCHEMAS) + FEW_SHOT_EXAMPLES
        static_tokens = count_tokens(static_block)
        billed_static_tokens = static_tokens // 10 if self.cache_hit else static_tokens

        compressed = self.compress_history()
        history_text = "\n".join(t.content for t in compressed)

        relevant_chunks = self.retrieve_relevant_chunks(user_input)
        doc_text = "\n".join(relevant_chunks)

        prompt = "\n".join([static_block, history_text, doc_text, user_input])
        effective_tokens = (
            billed_static_tokens
            + count_tokens(history_text)
            + count_tokens(doc_text)
            + count_tokens(user_input)
        )
        return prompt, effective_tokens


def demo():
    documents = [
        "Django ORM performance guide. " * 400,
        "PostgreSQL indexing strategies. " * 400,
        "JWT authentication flow details. " * 200,
    ]
    history = [Turn("user", f"Step {i}: tool call and result " * 50) for i in range(12)]
    user_input = "How should I index the orders table for JWT-authenticated queries?"

    naive = NaiveAgent(history=history, documents=documents)
    naive_prompt = naive.build_prompt(user_input)
    naive_tokens = count_tokens(naive_prompt)

    optimized_cold = OptimizedAgent(history=history, documents=documents, cache_hit=False)
    _, optimized_cold_tokens = optimized_cold.build_prompt(user_input)

    optimized_warm = OptimizedAgent(history=history, documents=documents, cache_hit=True)
    _, optimized_warm_tokens = optimized_warm.build_prompt(user_input)

    print(f"{'Naive (before)':<30} {naive_tokens:>10,} tokens")
    print(f"{'Optimized, cold cache':<30} {optimized_cold_tokens:>10,} tokens")
    print(f"{'Optimized, warm cache':<30} {optimized_warm_tokens:>10,} tokens")
    reduction = 100 * (1 - optimized_warm_tokens / naive_tokens)
    print(f"\nReduction (warm cache): {reduction:.1f}%")


if __name__ == "__main__":
    demo()
