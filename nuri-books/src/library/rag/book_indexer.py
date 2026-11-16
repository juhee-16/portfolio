"""도서 컬렉션: 질문 → 검색어 추출(프롬프트 1) → 정보나루 검색 → 후보 선별(프롬프트 2) → 색인."""
import json
import os

from langchain_openai import ChatOpenAI

from library import services

from . import config
from .indexer import get_collection, get_embeddings

GMS_BASE_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"


def _llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-5.4-nano",
        api_key=os.environ["GMS_KEY"],
        base_url=GMS_BASE_URL,
    )


def _parse_json(raw: str):
    """응답에서 JSON 부분만 꺼낸다. 실패하면 None."""
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s, e = raw.find(open_c), raw.rfind(close_c)
        if s != -1 and e != -1:
            try:
                return json.loads(raw[s : e + 1])
            except json.JSONDecodeError:
                continue
    return None


# ---------- 프롬프트 1: 검색어 추출 ----------
def extract_terms(question: str) -> list[str]:
    prompt = (
        "당신은 유아 그림책 사서입니다.\n"
        "교사의 질문에서 도서관 검색에 쓸 한국어 검색어를 뽑으세요.\n"
        f"- 최대 {config.MAX_QUERY_TERMS}개, 한 단어짜리 구체적인 명사 위주 "
        "(예: 환경 → 지구, 쓰레기, 재활용)\n"
        "- 그림책 제목에 실제로 들어갈 만한 말을 고르세요.\n"
        '반드시 JSON으로만 답하세요: {"terms": ["검색어1", "검색어2"]}\n\n'
        f"[질문]\n{question}"
    )
    data = _parse_json(_llm().invoke(prompt).content) or {}
    terms = [t.strip() for t in data.get("terms", []) if isinstance(t, str) and t.strip()]
    return list(dict.fromkeys(terms))[: config.MAX_QUERY_TERMS]


# ---------- 프롬프트 2: 후보 선별 ----------
def select_candidates(question: str, books: list[dict]) -> list[str]:
    """후보 중 질문에 맞는 책의 isbn13 목록을 돌려준다."""
    lines = [
        f"{b['isbn13']} | {b['bookname'].strip()} | {b.get('summary', '')}"
        for b in books
    ]
    prompt = (
        "당신은 만 3~5세 유아 대상 그림책 큐레이터입니다.\n"
        "[후보]에서 질문과 주제가 맞는 유아 그림책만 고르세요.\n"
        f"- 최대 {config.BOOK_KEEP}권\n"
        "- 성인·초등용 책, 주제와 무관한 책은 제외\n"
        "- 반드시 [후보]에 있는 isbn13만 쓰세요.\n"
        '반드시 JSON으로만 답하세요: {"selected": ["isbn13", "isbn13"]}\n\n'
        f"[질문]\n{question}\n\n[후보]\n" + "\n".join(lines)
    )
    data = _parse_json(_llm().invoke(prompt).content) or {}
    valid = {b["isbn13"] for b in books}
    return [i for i in data.get("selected", []) if i in valid]


# ---------- 재수집 방지 기록 ----------
def _load_collected() -> dict:
    if config.COLLECTED_PATH.exists():
        return json.loads(config.COLLECTED_PATH.read_text(encoding="utf-8"))
    return {}


def _save_collected(data: dict) -> None:
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    config.COLLECTED_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------- 수집 → 선별 → 색인 ----------
def _book_text(b: dict) -> str:
    return (
        f"{b['bookname'].strip()} / {b.get('authors', '')} / "
        f"{b.get('publisher', '')} / {b.get('description', '')}"
    )


def collect_books(question: str) -> dict:
    """질문 하나에 대해 수집·선별·색인을 한다. 이미 처리한 질문이면 건너뛴다."""
    key = question.strip()
    collected = _load_collected()
    if key in collected:
        return {"skipped": True, **collected[key]}

    terms = extract_terms(key)

    pool: dict[str, dict] = {}
    for t in terms:
        for b in services.search_books(t, True):
            pool.setdefault(b["isbn13"], b)
    candidates = services.add_summaries(list(pool.values())[: config.BOOK_CANDIDATES])

    selected_ids = set(select_candidates(key, candidates))
    selected = [b for b in candidates if b["isbn13"] in selected_ids]
    discarded = [b for b in candidates if b["isbn13"] not in selected_ids]

    if selected:
        col = get_collection(config.BOOK_COLLECTION)
        texts = [_book_text(b) for b in selected]
        col.upsert(
            ids=[b["isbn13"] for b in selected],
            documents=texts,
            embeddings=get_embeddings().embed_documents(texts),
            metadatas=[
                {
                    "isbn13": b["isbn13"],
                    "bookname": b["bookname"].strip(),
                    "authors": b.get("authors", ""),
                    "publisher": b.get("publisher", ""),
                    "source": "정보나루",
                }
                for b in selected
            ],
        )

    result = {
        "terms": terms,
        "indexed": [b["bookname"].strip() for b in selected],
        "discarded": [b["bookname"].strip() for b in discarded],
    }
    collected[key] = result
    _save_collected(collected)
    return {"skipped": False, **result}


if __name__ == "__main__":
    import time

    import django
    from dotenv import load_dotenv

    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_nuri.settings")
    django.setup()

    q = "환경 보호를 주제로 한 그림책을 추천해줘"
    t0 = time.time()
    r = collect_books(q)
    print(f"처리 시간: {time.time() - t0:.1f}초 / 수집 생략: {r['skipped']}")
    print("검색어:", r["terms"])
    print(f"색인된 책 ({len(r['indexed'])}권):")
    for n in r["indexed"]:
        print("  O", n)
    print(f"버려진 책 ({len(r['discarded'])}권):")
    for n in r["discarded"]:
        print("  X", n)
    print("도서 컬렉션 건수:", get_collection(config.BOOK_COLLECTION).count())