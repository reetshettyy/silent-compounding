from retrieval.build_index import load_documents
from retrieval.bm25_retriever import BM25Retriever


def test_bm25_retriever_shape():
    documents = load_documents("tasks/hotpotqa_sample.json")
    retriever = BM25Retriever(documents)

    results = retriever.retrieve(
        "Were Scott Derrickson and Ed Wood of the same nationality?",
        top_k=5,
    )

    assert len(results) == 5

    expected_keys = {
        "doc_id",
        "title",
        "text",
        "score",
        "rank",
    }

    for rank, result in enumerate(results, start=1):
        assert set(result.keys()) == expected_keys
        assert result["doc_id"]
        assert result["title"]
        assert result["text"]
        assert isinstance(result["score"], float)
        assert result["rank"] == rank
