from agents.research_agent import build_research_prompt


def test_no_confidence():
    agent_input = {
        "task_id": "test-001",
        "input_question": "What is the largest planet?",
        "retrieved_context": "Jupiter is the largest planet in the Solar System.",
    }

    prompt = build_research_prompt(agent_input)

    assert "confidence" not in prompt.lower()
