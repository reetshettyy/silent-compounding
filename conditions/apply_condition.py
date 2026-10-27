"""Turn a condition record into pipeline inputs (playbook Phase 4 matrix).

question        = what the agents are asked
retrieval_query = what BM25 searches with (so context comes from real retrieval)
The gold answer is never part of a condition record or of these inputs.
"""
CONDITION_IDS = ("C1", "C2", "C3", "C4")


def make_condition_input(record, condition_id):
    if condition_id not in CONDITION_IDS:
        raise ValueError(f"Unknown condition: {condition_id!r}")
    perturbed_question = condition_id in ("C2", "C4")
    perturbed_context = condition_id in ("C3", "C4")
    return {
        "task_id": record["task_id"],
        "condition_id": condition_id,
        "question": record["perturbed_question"] if perturbed_question else record["original_question"],
        "retrieval_query": record["perturbed_question"] if perturbed_context else record["original_question"],
        "perturbed_source_task_id": record["perturbed_source_task_id"],
        "perturbed_context_document_id": record["perturbed_context_document_id"],
        "seed": record["seed"],
        "offset": record["offset"],
    }
