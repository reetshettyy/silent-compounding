import agents.summarizer_agent as summarizer_agent


def test_summarizer_agent(monkeypatch):
    monkeypatch.setattr(
        summarizer_agent,
        "call_llm",
        lambda prompt: (
            "SUMMARY: Jupiter is the largest planet in our solar system."
        ),
    )

    result = summarizer_agent.summarize_node(
        {
            "task_id": "test-001",
            "input_question": "What is the largest planet?",
            "retrieved_context": (
                "FINDING: Jupiter is the largest planet.\n"
                "EVIDENCE: The provided context states this."
            ),
        }
    )

    output = result["summary_output"]

    assert isinstance(output["output"], str)
    assert output["output"].strip()
    assert "confidence" not in output
    assert len(result["trace"]) == 1
    assert result["trace"][0]["agent"] == "summarizer"
