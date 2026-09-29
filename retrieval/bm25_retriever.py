from typing import TypedDict

from rank_bm25 import BM25Okapi


class Document(TypedDict):
    doc_id: str
    title: str
    text: str


class RetrievedDocument(TypedDict):
    doc_id: str
    title: str
    text: str
    score: float
    rank: int


class BM25Retriever:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.tokenized_documents = [
            self._tokenize(document["text"])
            for document in documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_documents)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return text.lower().split()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        if not query.strip():
            raise ValueError("query must not be empty")

        scores = self.bm25.get_scores(self._tokenize(query))

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]

        results: list[RetrievedDocument] = []

        for rank, index in enumerate(ranked_indices, start=1):
            document = self.documents[index]

            results.append(
                {
                    "doc_id": document["doc_id"],
                    "title": document["title"],
                    "text": document["text"],
                    "score": float(scores[index]),
                    "rank": rank,
                }
            )

        return results
