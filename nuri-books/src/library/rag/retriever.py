"""질문과 가까운 근거를 벡터DB에서 Top-k개 찾는다."""
from . import config
from .indexer import get_collection, get_embeddings


def retrieve_nuri(question: str, k: int | None = None) -> list[dict]:
    """누리과정 컬렉션에서 질문과 가장 가까운 청크 k개를 돌려준다."""
    k = k or config.TOP_K
    col = get_collection(config.NURI_COLLECTION)
    if col.count() == 0:
        return [] 

    vector = get_embeddings().embed_query(question)
    res = col.query(query_embeddings=[vector], n_results=k)

    docs = []
    for text, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        docs.append({
            "text": text,
            "metadata": meta,
            "score": round(1 - dist, 3),  
        })
    return [d for d in docs if d["score"] >= config.MIN_SCORE]

def retrieve_books(question: str, k: int | None = None) -> list[dict]:
    """도서 컬렉션에서 질문과 가까운 책 k개를 돌려준다."""
    k = k or config.TOP_K
    col = get_collection(config.BOOK_COLLECTION)
    if col.count() == 0:
        return []

    vector = get_embeddings().embed_query(question)
    res = col.query(query_embeddings=[vector], n_results=min(k, col.count()))

    docs = []
    for text, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        docs.append({
            "text": text,
            "metadata": meta,
            "score": round(1 - dist, 3),
        })
    return [d for d in docs if d["score"] >= config.MIN_SCORE]