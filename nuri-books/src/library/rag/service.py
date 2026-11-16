"""view가 부르는 RAG 진입점. 결과를 화면용 dict로 바꾼다."""
import os
import re

from library.services import ServiceError

from . import config
from .graph import build_graph
from .indexer import get_collection

CITE_PATTERN = re.compile(r"\[근거\s*([\d,\s]+)\]")
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def ask_rag(question: str) -> dict:
    if not os.environ.get("GMS_KEY"):
        raise ServiceError("GMS_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
    if get_collection(config.NURI_COLLECTION).count() == 0:
        raise ServiceError(
            "색인된 누리과정 자료가 없습니다. "
            "`python -m library.rag.indexer`로 먼저 색인해 주세요."
        )

    try:
        result = _get_graph().invoke({"question": question, "docs": [], "answer": ""})
    except ServiceError:
        raise
    except Exception:
        # 오류 추적 정보·키가 화면에 노출되지 않게 일반 문구만 보여 준다 (NF2004)
        raise ServiceError("답변을 만드는 중 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.")

    docs = result["docs"]
    answer = result["answer"]
    numbers = {
        int(n)
        for g in CITE_PATTERN.findall(answer)
        for n in g.split(",")
        if n.strip().isdigit()
    }

    cited = []
    for i, d in enumerate(docs, start=1):
        if i not in numbers:
            continue
        m = d["metadata"]
        if d["source"] == "누리과정":
            title = f"{m['area']} > {m['category']}"
        else:
            title = m["bookname"]
        cited.append({
            "number": i,
            "source": d["source"],
            "title": title,
            "text": d["text"],
            "score": d["score"],
        })

    return {
        "answer": answer,
        "cited": cited,
        "topics": sorted({f"{d['metadata']['area']} > {d['metadata']['category']}"
                          for d in docs if d["source"] == "누리과정"}),
    }