"""LangGraph: retrieve → generate 두 노드."""
import os
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from . import config
from .book_indexer import collect_books
from .retriever import retrieve_books, retrieve_nuri

GMS_BASE_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"


class RagState(TypedDict):
    question: str
    docs: list[dict]
    answer: str


def _wants_books(question: str) -> bool:
    return any(w in question for w in config.BOOK_INTENT_WORDS)


def retrieve(state: RagState) -> dict:
    q = state["question"]
    if _wants_books(q):
        collect_books(q)   # 정보나루 수집·선별·색인 (같은 질문이면 생략)

    nuri = retrieve_nuri(q)
    books = retrieve_books(q)

    # 출처 표시 + 중복 제거(content_id / isbn13 기준)
    docs, seen = [], set()
    for d in nuri:
        d["source"] = "누리과정"
        key = d["metadata"]["content_id"]
        if key not in seen:
            seen.add(key)
            docs.append(d)
    for d in books:
        d["source"] = "도서 정보"
        key = d["metadata"]["isbn13"]
        if key not in seen:
            seen.add(key)
            docs.append(d)
    return {"docs": docs}


def generate(state: RagState) -> dict:
    docs = state["docs"]
    if not docs:
        return {"answer": "관련 근거를 찾지 못해 확인되지 않습니다."}

    context = "\n\n".join(
        f"[근거 {i}] ({d['source']}) {d['text']}" for i, d in enumerate(docs, start=1)
    )
    prompt = (
        "당신은 유치원 교사를 돕는 누리과정·그림책 안내자입니다.\n"
        "아래 [근거]에 있는 내용만 사용해 답하고, 근거 뒤에 [근거 N]을 붙이세요.\n"
        "그림책을 추천할 때는 '도서 정보' 근거의 책만 언급하세요.\n"
        "[근거]에 없는 내용은 추측하지 말고 '확인되지 않습니다'라고 답하세요.\n"
        "모든 문장은 '~입니다/~합니다'로 끝내세요.\n\n"
        f"[근거]\n{context}\n\n[질문]\n{state['question']}"
    )
    llm = ChatOpenAI(
        model="gpt-5.4-nano",
        api_key=os.environ["GMS_KEY"],
        base_url=GMS_BASE_URL,
    )
    return {"answer": llm.invoke(prompt).content}


def build_graph():
    g = StateGraph(RagState)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


if __name__ == "__main__":
    import django
    from dotenv import load_dotenv

    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_nuri.settings")
    django.setup()

    app = build_graph()
    print("노드:", list(app.get_graph().nodes))
    question = "신체활동과 관련된 누리과정 내용을 알려줘"
    result = app.invoke({"question": question, "docs": [], "answer": ""})
    print("--- 답변 ---")
    print(result["answer"])
    print("--- 근거 목록 ---")
    for i, d in enumerate(result["docs"], start=1):
        print(i, f"({d['source']})", d["score"], d["text"][:60])