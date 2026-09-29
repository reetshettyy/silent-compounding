import json
from pathlib import Path

from conditions.build_conditions import (
    build_conditions,
    build_condition_matrix,
)


SAMPLE_PATH = Path("tasks/hotpotqa_sample.json")


def test_four_conditions_per_task():
    records = build_conditions(
        sample_path=SAMPLE_PATH,
        seed=42,
        offset=1,
    )

    assert len(records) == 10

    for record in records:
        conditions = build_condition_matrix(record)

        assert len(conditions) == 4
        assert [c["condition_id"] for c in conditions] == [
            "C1",
            "C2",
            "C3",
            "C4",
        ]

        assert conditions[0]["question"] == record["original_question"]
        assert conditions[0]["context"] == record["original_context"]

        assert conditions[1]["question"] == record["perturbed_question"]
        assert conditions[1]["context"] == record["original_context"]

        assert conditions[2]["question"] == record["original_question"]
        assert conditions[2]["context"] == record["perturbed_context"]

        assert conditions[3]["question"] == record["perturbed_question"]
        assert conditions[3]["context"] == record["perturbed_context"]


def test_required_task_fields():
    records = build_conditions(
        sample_path=SAMPLE_PATH,
        seed=42,
        offset=1,
    )

    required_fields = {
        "original_question",
        "perturbed_question",
        "original_context",
        "perturbed_context",
        "condition_id",
        "perturbation_type",
        "perturbation_description",
    }

    for record in records:
        assert required_fields.issubset(record.keys())
        assert record["original_question"] != record["perturbed_question"]


def test_reproducibility_same_seed_same_perturbations():
    first = build_conditions(
        sample_path=SAMPLE_PATH,
        seed=42,
        offset=1,
    )

    second = build_conditions(
        sample_path=SAMPLE_PATH,
        seed=42,
        offset=1,
    )

    first_mapping = [
        (
            record["task_id"],
            record["perturbed_source_task_id"],
            record["perturbed_question"],
            record["perturbed_context_document_id"],
        )
        for record in first
    ]

    second_mapping = [
        (
            record["task_id"],
            record["perturbed_source_task_id"],
            record["perturbed_question"],
            record["perturbed_context_document_id"],
        )
        for record in second
    ]

    assert first_mapping == second_mapping


def test_gold_answer_not_stored_in_condition_records():
    with SAMPLE_PATH.open("r", encoding="utf-8") as file:
        tasks = json.load(file)

    records = build_conditions(
        sample_path=SAMPLE_PATH,
        seed=42,
        offset=1,
    )

    gold_answers = {
        task["task_id"]: task["gold_answer"]
        for task in tasks
    }

    for record in records:
        assert "gold_answer" not in record

        for condition in build_condition_matrix(record):
            assert "gold_answer" not in condition

        # The condition-building interface does not receive the gold answer.
        assert gold_answers[record["task_id"]] not in {
            record["perturbation_type"],
            record["perturbation_description"],
        }


def test_condition_inputs_are_prompt_safe():
    records = build_conditions(
        sample_path=SAMPLE_PATH,
        seed=42,
        offset=1,
    )

    allowed_prompt_fields = {
        "task_id",
        "condition_id",
        "question",
        "context",
    }

    for record in records:
        for condition in build_condition_matrix(record):
            assert set(condition.keys()) == allowed_prompt_fields
            assert "gold_answer" not in condition
