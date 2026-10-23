import agents.action_agent as action_agent


def test_action_agent(monkeypatch):
    monkeypatch.setattr(
        action_agent,
        "call_llm",
        lambda prompt: "FINAL ANSWER: Jupiter.",
    )

    result = action_agent.action_node(
        {
            "task_id": "test-001",
            "input_question": "What is the largest planet?",
            "retrieved_context": (
                "SUMMARY: Jupiter is the largest planet in our solar system."
            ),
        }
    )

    output = result["action_output"]

    assert isinstance(output["output"], str)
    assert output["output"].strip()
    assert "confidence" not in output
    assert len(result["trace"]) == 1
    assert result["trace"][0]["agent"] == "action"
