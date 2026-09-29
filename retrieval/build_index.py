import json
from pathlib import Path
from typing import TypedDict

from rank_bm25 import BM25Okapi


class Document(TypedDict):
    doc_id: str
    title: str
    text: str


def tokenize(text: str) -> list[str]:
    return text.lower().split()


def load_documents(sample_path: str | Path) -> list[Document]:
    sample_path = Path(sample_path)

    with sample_path.open("r", encoding="utf-8") as f:
        tasks = json.load(f)

    documents: list[Document] = []

    for task in tasks:
        task_id = task["task_id"]
        titles = task["context"]["title"]
        sentence_groups = task["context"]["sentences"]

        if len(titles) != len(sentence_groups):
            raise ValueError(
                f"{task_id}: title/sentence-group length mismatch "
                f"({len(titles)} != {len(sentence_groups)})"
            )

        for index, (title, sentences) in enumerate(
            zip(titles, sentence_groups)
        ):
            text = " ".join(sentence.strip() for sentence in sentences).strip()

            documents.append(
                {
                    "doc_id": f"{task_id}_DOC{index:02d}",
                    "title": title,
                    "text": text,
                }
            )

    return documents


def build_index(
    documents: list[Document],
) -> tuple[BM25Okapi, list[Document]]:
    tokenized_documents = [
        tokenize(document["text"])
        for document in documents
    ]

    bm25 = BM25Okapi(tokenized_documents)

    return bm25, documents


def main() -> None:
    sample_path = Path("tasks/hotpotqa_sample.json")

    documents = load_documents(sample_path)
    bm25, documents = build_index(documents)

    print(f"Loaded documents: {len(documents)}")
    print(f"BM25 index documents: {len(bm25.doc_freqs)}")

    print("\nFirst 3 indexed documents:")
    for document in documents[:3]:
        print("-" * 60)
        print(f"doc_id: {document['doc_id']}")
        print(f"title:  {document['title']}")
        print(f"text:   {document['text']}")

    print("\nBUILD_INDEX: OK")


if __name__ == "__main__":
    main()
