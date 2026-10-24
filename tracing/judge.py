"""Independent semantic answer evaluator.

This module is separate from the generation pipeline.
The reference answer is used only for evaluation.
"""

import json
import re
from pathlib import Path
import yaml

from langchain_ollama import ChatOllama


JUDGE_MODEL = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))["models"]["evaluator_model"]
VALID_VERDICTS = {"correct", "incorrect", "uncertain"}


def build_judge_prompt(question: str, predicted_answer: str, gold_answer: str) -> str:
    """Build an evaluation-only prompt; never pass it to generation agents."""
    return f"""You are an independent answer evaluator.

Assess whether the predicted answer correctly answers the question.
Accept semantically equivalent paraphrases and equivalent answer formats.
Do not accept contradictions, unsupported claims that change the answer,
or answers that merely mention the reference answer.
If the question requests a specific entity or level of detail, an answer
that gives only a broader category is incorrect when it fails to answer
the question at the requested specificity.
Use uncertain only when correctness genuinely cannot be determined
from the question, reference answer, and prediction.

Return ONLY one valid JSON object with exactly these keys:
{{
  "verdict": "correct" | "incorrect" | "uncertain",
  "rationale": "brief explanation"
}}

Question:
{question}

Reference answer (evaluation only):
{gold_answer}

Predicted answer:
{predicted_answer}
"""


def parse_judge_response(response: str) -> dict:
    """Parse and validate the evaluator's JSON response."""
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Judge response is empty.")

    candidate = response.strip()
    candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
    candidate = re.sub(r"\s*```$", "", candidate)

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Judge response is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("Judge response must be a JSON object.")

    if set(data) != {"verdict", "rationale"}:
        raise ValueError("Judge JSON must contain exactly verdict and rationale.")

    if data["verdict"] not in VALID_VERDICTS:
        raise ValueError(f"Invalid verdict: {data['verdict']!r}")

    if not isinstance(data["rationale"], str) or not data["rationale"].strip():
        raise ValueError("Judge rationale must be a non-empty string.")

    return {
        "verdict": data["verdict"],
        "rationale": data["rationale"].strip(),
        "judge_model": JUDGE_MODEL,
        "evaluation_method": "llm_semantic_judge",
    }


def judge_answer(question: str, predicted_answer: str, gold_answer: str) -> dict:
    """Evaluate one answer using the separate local Mistral model."""
    if not all(
        isinstance(value, str) and value.strip()
        for value in (question, predicted_answer, gold_answer)
    ):
        raise ValueError("Question, predicted answer, and reference answer must be non-empty.")

    llm = ChatOllama(
        model=JUDGE_MODEL,
        temperature=0,
        num_predict=200,
        format="json",
    )
    response = llm.invoke(
        build_judge_prompt(question, predicted_answer, gold_answer)
    ).content

    result = parse_judge_response(response)
    result["question"] = question
    result["predicted_answer"] = predicted_answer
    result["gold_answer"] = gold_answer
    return result
