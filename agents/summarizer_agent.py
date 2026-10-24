from typing import TypedDict
from pathlib import Path
import yaml

from langchain_ollama import ChatOllama


class AgentInput(TypedDict):
    task_id: str
    input_question: str
    retrieved_context: str


class TaskRecord(TypedDict):
    gold_answer: str
    supporting_facts: list
    original_question: str
    original_context: str

llm = ChatOllama(model=yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))["models"]["summarizer_model"], temperature=0.5, max_tokens=250)


def call_llm(prompt: str) -> str:
    return llm.invoke(prompt).content


def build_summarizer_prompt(agent_input: AgentInput) -> str:
    return f"""
Summarize the following research output.

Preserve:
- The main finding
- The important supporting facts

Do not add new facts or information that is not present in the research output.

Research output:

{agent_input["retrieved_context"]}

Respond in exactly this format:

SUMMARY: <concise summary of the main finding and supporting facts>

"""


def summarize_node(agent_input: AgentInput, trace=None):
    prompt = build_summarizer_prompt(agent_input)
    output = call_llm(prompt)

    structured_output = {
        "output": output,
    }

    trace = [] if trace is None else trace
    trace.append(
        {
            "agent": "summarizer",
            "output": structured_output,
        }
    )

    return {
        "summary_output": structured_output,
        "trace": trace,
    }
