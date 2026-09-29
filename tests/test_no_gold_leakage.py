from agents.research_agent import build_research_prompt


def test_no_gold_leakage():
    agent_input = {
        "task_id": "test-001",
        "input_question": "Which planet is the largest in our solar system?",
        "retrieved_context": (
            "The largest planet in the Solar System is a gas giant "
            "with a very large mass and volume."
        ),
    }

    task = {
        "gold_answer": "Jupiter",
        "supporting_facts": ["The largest planet in the Solar System is a gas giant."],
        "original_question": "Which planet is the largest in our solar system?",
        "original_context": (
            "The largest planet in the Solar System is a gas giant "
            "with a very large mass and volume."
        ),
    }

    prompt = build_research_prompt(agent_input)

    assert task["gold_answer"] not in prompt
