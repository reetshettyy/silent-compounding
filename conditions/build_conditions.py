import json
import random
import os
import sys
from pathlib import Path

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    ),
)

from retrieval.build_index import load_documents
from retrieval.bm25_retriever import BM25Retriever


DEFAULT_SEED = 42
DEFAULT_OFFSET = 1


def choose_perturbed_question_indices(
    number_of_tasks: int,
    seed: int = DEFAULT_SEED,
    offset: int = DEFAULT_OFFSET,
) -> list[int]:
    if number_of_tasks < 2:
        raise ValueError("At least two tasks are required.")

    if offset % number_of_tasks == 0:
        raise ValueError(
            "Offset must select a different question."
        )

    indices = list(range(number_of_tasks))
    rng = random.Random(seed)
    rng.shuffle(indices)

    return [
        indices[(position + offset) % number_of_tasks]
        for position in range(number_of_tasks)
    ]


def build_conditions(
    sample_path: str | Path,
    seed: int = DEFAULT_SEED,
    offset: int = DEFAULT_OFFSET,
) -> list[dict]:
    sample_path = Path(sample_path)

    with sample_path.open("r", encoding="utf-8") as file:
        tasks = json.load(file)

    if len(tasks) < 2:
        raise ValueError("At least two tasks are required.")

    documents = load_documents(sample_path)
    retriever = BM25Retriever(documents)

    perturbed_indices = choose_perturbed_question_indices(
        number_of_tasks=len(tasks),
        seed=seed,
        offset=offset,
    )

    conditions = []

    for index, task in enumerate(tasks):
        perturbed_index = perturbed_indices[index]

        if perturbed_index == index:
            raise ValueError(
                f"Task {task['task_id']} was paired with itself."
            )

        perturbed_task = tasks[perturbed_index]

        retrieved = retriever.retrieve(
            query=perturbed_task["question"],
            top_k=1,
        )

        if not retrieved:
            raise ValueError(
                f"No retrieved context for task {perturbed_task['task_id']}."
            )

        top_document = retrieved[0]

        original_context = "\n".join(
            f"TITLE: {title}\n"
            + "\n".join(sentences)
            for title, sentences in zip(
                task["context"]["title"],
                task["context"]["sentences"],
            )
        )

        perturbed_context = (
            f"TITLE: {top_document['title']}\n"
            f"{top_document['text']}"
        )

        conditions.append(
            {
                "task_id": task["task_id"],
                "original_question": task["question"],
                "perturbed_question": perturbed_task["question"],
                "original_context": original_context,
                "perturbed_context": perturbed_context,
                "condition_id": "C1-C4",
                "perturbation_type": "question_and_context_source",
                "perturbation_description": (
                    "Perturbed question selected deterministically "
                    f"using seed={seed}, offset={offset}; "
                    "perturbed context is the top-1 BM25 retrieval "
                    "for that perturbed question."
                ),
                "seed": seed,
                "offset": offset,
                "perturbed_source_task_id": perturbed_task["task_id"],
                "perturbed_context_document_id": top_document["doc_id"],
                "perturbed_context_title": top_document["title"],
            }
        )

    return conditions


def build_condition_matrix(condition_record: dict) -> list[dict]:
    return [
        {
            "task_id": condition_record["task_id"],
            "condition_id": "C1",
            "question": condition_record["original_question"],
            "context": condition_record["original_context"],
        },
        {
            "task_id": condition_record["task_id"],
            "condition_id": "C2",
            "question": condition_record["perturbed_question"],
            "context": condition_record["original_context"],
        },
        {
            "task_id": condition_record["task_id"],
            "condition_id": "C3",
            "question": condition_record["original_question"],
            "context": condition_record["perturbed_context"],
        },
        {
            "task_id": condition_record["task_id"],
            "condition_id": "C4",
            "question": condition_record["perturbed_question"],
            "context": condition_record["perturbed_context"],
        },
    ]


def main() -> None:
    sample_path = Path("tasks/hotpotqa_sample.json")
    output_path = Path("conditions/condition_records.json")

    records = build_conditions(
        sample_path=sample_path,
        seed=DEFAULT_SEED,
        offset=DEFAULT_OFFSET,
    )

    matrix = []
    for record in records:
        matrix.extend(build_condition_matrix(record))

    output = {
        "seed": DEFAULT_SEED,
        "offset": DEFAULT_OFFSET,
        "records": records,
        "conditions": matrix,
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"Tasks: {len(records)}")
    print(f"Conditions: {len(matrix)}")
    print(f"Seed: {DEFAULT_SEED}")
    print(f"Offset: {DEFAULT_OFFSET}")
    print(f"Output: {output_path}")
    print("BUILD_CONDITIONS: OK")


if __name__ == "__main__":
    main()
