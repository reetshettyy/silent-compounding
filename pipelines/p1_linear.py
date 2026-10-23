import json
import os
import sys
from time import perf_counter
from typing import TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from langgraph.graph import END, StateGraph

from agents.research_agent import research_node
from agents.summarizer_agent import summarize_node
from agents.action_agent import action_node
from injection.injector import inject_error
from retrieval.build_index import load_documents
from retrieval.bm25_retriever import BM25Retriever
from tracing.logger import log_run, save_raw_trace


class PipelineState(TypedDict):
    task_id: str
    question: str
    context: dict
    research_output: dict
    summary: dict
    final_answer: dict
    trace: list
    inject: bool
    error_type: str | None
    wording: str | None
    seed: int | None


def research_node_adapter(state):
    top_k = 5
    retrieval_start = perf_counter()

    results = retriever.retrieve(
        query=state["question"],
        top_k=top_k,
    )

    retrieval_latency = perf_counter() - retrieval_start

    state["trace"].append(
        {
            "agent": "retriever",
            "retrieval": {
                "query": state["question"],
                "retriever_type": "BM25",
                "top_k": top_k,
                "retrieved_document_ids": [
                    result["doc_id"] for result in results
                ],
                "retrieved_titles": [
                    result["title"] for result in results
                ],
                "retrieval_scores": [
                    result["score"] for result in results
                ],
                "retrieval_rank": [
                    result["rank"] for result in results
                ],
                "retrieval_latency": retrieval_latency,
            },
        }
    )

    context_text = ""

    for result in results:
        context_text += (
            f"\\nTITLE: {result['title']}\\n"
            f"{result['text']}\\n"
        )

    agent_input = {
        "task_id": state["task_id"],
        "input_question": state["question"],
        "retrieved_context": context_text,
    }

    result = research_node(
        agent_input,
        trace=state["trace"],
    )

    research_output = result["research_output"]
    trace = result["trace"]

    if not state.get("inject", False):
        return {
            "research_output": research_output,
            "trace": trace,
        }

    error_type = state.get("error_type")
    wording = state.get("wording")

    if not error_type:
        raise ValueError(
            "error_type must be provided when inject=True."
        )

    if not wording:
        raise ValueError(
            "wording must be provided when inject=True."
        )

    clean_output = research_output.get("output", "")

    corrupted_output, error_template = inject_error(
        clean_output=clean_output,
        error_type=error_type,
        wording=wording,
        injection_stage="research",
        seed=state.get("seed"),
    )

    injected_research_output = dict(research_output)
    injected_research_output["output"] = corrupted_output

    trace.append(
        {
            "agent": "error_injector",
            "output": {
                "error_type": error_template.error_type,
                "injection_stage": "research",
                "wording": wording,
                "original_claim": error_template.original_claim_pattern,
                "injected_claim": error_template.injected_claim,
                "injection_description": error_template.description,
                "corrupted_output": corrupted_output,
            },
        }
    )

    return {
        "research_output": injected_research_output,
        "trace": trace,
    }


def summarize_node_adapter(state):
    agent_input = {
        "task_id": state["task_id"],
        "input_question": state["question"],
        "retrieved_context": state["research_output"]["output"],
    }

    result = summarize_node(
        agent_input,
        trace=state["trace"],
    )

    return {
        "summary": result["summary_output"],
        "trace": result["trace"],
    }


def action_node_adapter(state):
    agent_input = {
        "task_id": state["task_id"],
        "input_question": state["question"],
        "retrieved_context": state["summary"]["output"],
    }

    result = action_node(
        agent_input,
        trace=state["trace"],
    )

    return {
        "final_answer": result["action_output"],
        "trace": result["trace"],
    }


documents = load_documents("tasks/hotpotqa_sample.json")
retriever = BM25Retriever(documents)

graph = StateGraph(PipelineState)

graph.add_node("research", research_node_adapter)
graph.add_node("summarize", summarize_node_adapter)
graph.add_node("action", action_node_adapter)

graph.set_entry_point("research")

graph.add_edge("research", "summarize")
graph.add_edge("summarize", "action")
graph.add_edge("action", END)

pipeline = graph.compile()


def run_pipeline(
    task,
    inject=False,
    error_type=None,
    wording=None,
    seed=None,
):
    initial_state = {
        "task_id": task["task_id"],
        "question": task["question"],
        "context": task["context"],
        "research_output": {},
        "summary": {},
        "final_answer": {},
        "trace": [],
        "inject": inject,
        "error_type": error_type,
        "wording": wording,
        "seed": seed,
    }

    return pipeline.invoke(initial_state)


if __name__ == "__main__":
    with open("tasks/hotpotqa_sample.json", "r") as file:
        tasks = json.load(file)

    print(f"Loaded {len(tasks)} questions.")

    for task in tasks:
        final_state = run_pipeline(
            task,
            inject=False,
            error_type=None,
            wording=None,
        )

        run_id = task["task_id"]

        raw_trace_path = save_raw_trace(
            run_id,
            final_state["trace"],
        )

        final_answer = final_state["final_answer"]

        log_run(
            {
                "run_id": run_id,
                "pipeline": "P1",
                "model": "llama3.1",
                "task_id": task["task_id"],
                "error_type": None,
                "injection_stage": None,
                "wording": None,
                "error_detected": None,
                "correction_stage": None,
                "final_error": None,
                "severity": None,
                # Retained in the CSV schema for legacy compatibility.
                # Current methodology does not collect confidence scores.
                "self_reported_confidence": None,
                "actual_correct": None,
                "raw_trace_path": raw_trace_path,
            }
        )

        print("\n" + "=" * 80)
        print(f"TASK: {task['task_id']}")
        print(f"QUESTION: {task['question']}")
        print(f"GOLD ANSWER: {task['gold_answer']}")
        print(f"FINAL ANSWER: {final_answer}")
        print(f"RAW TRACE: {raw_trace_path}")
        print("=" * 80)