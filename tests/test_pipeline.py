
from fixed_pipeline import SCHEMA, run_pipeline, validate_schema
from pipeline import NaiveAgent, OptimizedAgent, Turn, count_tokens


def test_optimized_uses_fewer_tokens_than_naive():
    docs = ["doc content " * 300]
    history = [Turn("user", "step " * 20) for _ in range(10)]
    naive = NaiveAgent(history=history, documents=docs)
    optimized = OptimizedAgent(history=history, documents=docs, cache_hit=True)

    naive_tokens = count_tokens(naive.build_prompt("query"))
    _, opt_tokens = optimized.build_prompt("query")

    assert opt_tokens < naive_tokens


def test_history_compression_keeps_recent_turns_verbatim():
    history = [Turn("user", f"turn-{i}") for i in range(10)]
    agent = OptimizedAgent(history=history, keep_last=3)
    compressed = agent.compress_history()

    assert compressed[-1].content == "turn-9"
    assert compressed[-3].content == "turn-7"
    assert "Summary" in compressed[0].content


def test_retrieval_returns_top_k_chunks():
    docs = ["irrelevant text " * 100, "JWT authentication flow details " * 100]
    agent = OptimizedAgent(documents=docs)
    chunks = agent.retrieve_relevant_chunks("JWT authentication", top_k=2)
    assert len(chunks) == 2
    assert "JWT" in chunks[0]


def test_schema_validation_rejects_bad_shape():
    assert validate_schema({"user_id": "u1", "score": 5, "verdict": "x"}, SCHEMA)
    assert not validate_schema({"user_id": "u1", "score": "5", "verdict": "x"}, SCHEMA)
    assert not validate_schema({"user_id": "u1"}, SCHEMA)


def test_pipeline_never_returns_malformed_or_wrong_data():
    for i in range(50):
        result = run_pipeline(user_id=f"u{i}")
        assert result["status"] in ("success", "timeout")
        if result["status"] == "success":
            assert result["result"]["user_id"] == f"u{i}"
