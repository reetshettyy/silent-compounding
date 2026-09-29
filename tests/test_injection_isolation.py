import injection.injector as injector


def test_injection_uses_only_clean_agent_output(monkeypatch):
    clean_output = "Scott Derrickson directed Doctor Strange."
    gold_answer = "The correct answer is unrelated to the injected claim."

    captured = {}

    class FakeTemplate:
        error_type = "factual"
        original_claim_pattern = clean_output
        injected_claim = "James Cameron directed Doctor Strange."
        description = "Controlled factual substitution"

    def fake_generate_corrupted_claim(**kwargs):
        captured.update(kwargs)
        return FakeTemplate()

    monkeypatch.setattr(
        injector,
        "generate_corrupted_claim",
        fake_generate_corrupted_claim,
    )

    corrupted_output, template = injector.inject_error(
        clean_output=clean_output,
        error_type="factual",
        wording="neutral",
        injection_stage="research",
        seed=42,
    )

    # The injector receives the agent output, not the gold answer.
    assert captured["research_output"] == clean_output
    assert "gold_answer" not in captured

    # The gold answer cannot appear in the resulting corrupted output.
    assert gold_answer not in corrupted_output

    # Only the controlled claim substitution occurred.
    assert corrupted_output == "James Cameron directed Doctor Strange."

    assert template.error_type == "factual"
    assert template.original_claim_pattern == clean_output
    assert template.injected_claim == corrupted_output
