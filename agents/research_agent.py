from typing import TypedDict

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


llm = ChatOllama(
    model="llama3.1",
    temperature=0,
    max_tokens=300,
)


def call_llm(prompt: str) -> str:
    return llm.invoke(prompt).content


def build_research_prompt(agent_input: AgentInput) -> str:
    return f"""
Answer the following question using ONLY the provided HotpotQA context.

Do not use outside knowledge.
Do not invent facts.
Do not claim that you searched Google, websites, databases, or other sources.
Do not mention sources that are not present in the provided context.

Question:
{agent_input["input_question"]}

Provided context:
{agent_input["retrieved_context"]}

Identify the relevant facts from the context and use them to answer the question.

Respond in exactly this format:

FINDING: <your answer or main finding>

EVIDENCE: <the specific facts from the provided context that support the finding>

"""


def research_node(agent_input: AgentInput, trace=None):
    prompt = build_research_prompt(agent_input)
    output = call_llm(prompt)

    structured_output = {
        "output": output,
    }

    trace = [] if trace is None else trace
    trace.append(
        {
            "agent": "research",
            "output": structured_output,
        }
    )

    return {
        "research_output": structured_output,
        "trace": trace,
    }
