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

llm = ChatOllama(model=yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))["models"]["answer_model"], temperature=0.5, max_tokens=250)


def call_llm(prompt: str) -> str:
    return llm.invoke(prompt).content


def build_action_prompt(agent_input: AgentInput) -> str:
    return f"""
Answer the user's question using the provided summary.

Question:
{agent_input["input_question"]}

Summary:
{agent_input["retrieved_context"]}

Give a clear final answer based only on the information in the summary.

Respond in exactly this format:

FINAL ANSWER: <your answer to the question>

"""


def action_node(agent_input: AgentInput, trace=None):
    prompt = build_action_prompt(agent_input)
    output = call_llm(prompt)

    structured_output = {
        "output": output,
    }

    trace = [] if trace is None else trace
    trace.append(
        {
            "agent": "action",
            "output": structured_output,
        }
    )

    return {
        "action_output": structured_output,
        "trace": trace,
    }
