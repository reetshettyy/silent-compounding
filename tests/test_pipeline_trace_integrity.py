from pathlib import Path


def test_injected_research_trace_matches_downstream_input():
    source = Path("pipelines/p1_linear.py").read_text()

    # The pipeline must preserve the clean output for auditing.
    assert 'original_output = clean_output' in source
    assert '"original_output": original_output' in source

    # The research trace must be updated with the injected output.
    assert 'trace_item["output"] = dict(injected_research_output)' in source

    # The downstream summarizer consumes the research output in state.
    assert 'state["research_output"]["output"]' in source

    # The injector must fail rather than silently omit the research trace.
    assert "Cannot record injected output: research trace entry is missing." in source
