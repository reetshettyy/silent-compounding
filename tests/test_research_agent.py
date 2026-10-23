import agents.research_agent as research_agent


def test_research_agent(monkeypatch):
    monkeypatch.setattr(
        research_agent,
        "call_llm",
        lambda prompt: (
            "FINDING: Jupiter is the largest planet.\n"
            "EVIDENCE: The provided context states this."
        ),
    )

    result = research_agent.research_node(
        {
            "task_id": "test-001",
            "input_question": "What is the largest planet?",
            "retrieved_context": (
                "Jupiter is the largest planet in the Solar System."
            ),
        }
    )

    assert "research_output" in result
    assert "trace" in result
    assert len(result["trace"]) == 1
    assert result["trace"][0]["agent"] == "research"
    assert isinstance(result["research_output"]["output"], str)
    assert "confidence" not in result["research_output"]
