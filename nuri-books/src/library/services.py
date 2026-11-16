"""누리과정 그림책 수업 플래너의 핵심 로직 (Streamlit/Django와 무관한 순수 파이썬).

- 도서관 정보나루 API 호출
- 누리과정 JSON 로드, 키워드 → 내용범주 매칭
- 근거 문서 수집, 프롬프트 조립, LLM 호출, 인용 근거 추출
"""

import html
import json
import os
import re
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()
logger = logging.getLogger(__name__)

GMS_BASE_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"

# --- 도서관 정보나루 API 설정 ---
LIBRARY_KEY_NAMES = ("DATA4LIBRARY_KEY",)
DATA4LIBRARY_BASE = "https://data4library.kr/api"
DAILY_LIMIT = 450  # 정보나루 한도(500)보다 여유 있게

# --- 누리과정 JSON 경로: nuri_django/data/nuri_curriculum.json ---
# 파일 이름이 다르면 여기만 바꾸세요.
CURRICULUM_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "nuri_curriculum.json"
)

DOMAIN = "유아동 그림책"

# [FR-04] 모든 추천 결과 하단에 표시할 면책 문구
DISCLAIMER = (
    "⚠️ 본 답변은 수업 설계를 위한 교육 참고용 자료이며, 아동 개인에 대한"
    " 심리·의료적 진단이나 평가를 대신하지 않습니다."
)

# 답변 본문의 [근거 3], [근거 3, 5] 표기를 찾는다.
CITE_PATTERN = re.compile(r"\[근거\s*([\d,\s]+)\]")

AGE_LABELS = {"3": "만 3세", "4": "만 4세", "5": "만 5세"}

# 추천 질문 버튼 (키 → (버튼 이름, 질문))
PRESET_PROMPTS = {
    "link": (
        "🌱 누리과정 영역 연계",
        "선택한 그림책과 연계할 수 있는 2019 개정 누리과정 영역과 내용범주를 알려줘.",
    ),
    "extend": (
        "🎨 교실 수업 확장 활동",
        "이 그림책을 활용해 교실 흥미영역(언어, 미술, 역할, 쌓기 등)에서 진행할 수 있는 확장 놀이 활동을 제안해줘.",
    ),
    "interact": (
        "💬 교사-유아 상호작용 지침",
        "아이들의 놀이를 몰입시키고 발문을 확장할 수 있는 교사-유아 발문 가이드 및 발문 예시를 작성해줘.",
    ),
}

# 사이드바에 보여줄 키워드 수 (누리과정 내용범주마다)
KEYWORDS_PER_CATEGORY = 3
KEYWORDS_WHEN_CATEGORY_SELECTED = 8

# 한 번에 화면에 보여줄 도서 수 (많을수록 상세조회 API 호출이 늘어난다)
BOOK_LIMIT = 8

# 월별 놀이 주제 키워드 → 도서 검색어
# 비워 두면 사이드바에 보이는 키워드 이름이 그대로 검색어가 된다.
# 특정 키워드만 다르게 검색하고 싶을 때 {"키워드": ["검색어"]} 형태로 추가한다.
KEYWORD_SEARCH_MAP: dict[str, list[str]] = {
    "우리나라": ["한복", "김치", "한옥", "윷놀이", "설날", "추석", "전래동화", "태극기"],
    "봄": ["봄날", "봄꽃", "봄나들이", "새싹", "개구리", "나비"],
    "색과모양": ["알록달록", "무지개", "동그라미", "네모", "세모", "색깔"],
    "교통기관": ["자동차", "기차", "버스", "비행기", "지하철", "자전거"],
    "우리동네": ["동네", "마을", "이웃", "시장", "소방관", "도서관"],
    "환경": ["지구", "쓰레기", "재활용", "북극곰", "멸종", "바다", "숲", "물"],
}

class ServiceError(Exception):
  """사용자에게 그대로 보여 줄 수 있는 오류 메시지를 담는 예외."""


# =========================
# 누리과정 JSON
# =========================
@lru_cache(maxsize=1)
def _load():
  try:
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
      data = json.load(f)
  except Exception as e:
    raise ServiceError(
        f"누리과정 파일을 불러오지 못했습니다. 경로를 확인하세요: {e}"
    ) from e

  areas = {a["area_id"]: a for a in data["areas"]}
  categories = [
      {**c, "area_id": a["area_id"], "area": a["area"], "area_goal": a["goal"]}
      for a in data["areas"]
      for c in a["categories"]
  ]
  by_id = {c["category_id"]: c for c in categories}
  return data, areas, categories, by_id


def get_curriculum() -> dict:
  return _load()[0]


def get_areas() -> dict:
  return _load()[1]


def get_categories() -> list[dict]:
  return _load()[2]


def get_categories_by_id() -> dict:
  return _load()[3]


# =========================
# 누리과정 주제 선택·매칭 (FR-01, FR-03)
# =========================
def pool_categories(area_id: str | None, category_id: str | None) -> list[dict]:
  """선택한 영역·내용범주에 해당하는 내용범주 목록."""
  return [
      c
      for c in get_categories()
      if (not area_id or c["area_id"] == area_id)
      and (not category_id or c["category_id"] == category_id)
  ]


def keyword_groups(area_id: str | None, category_id: str | None) -> list[dict]:
  """누리과정 내용범주별로 대표 키워드만 골라 묶는다. (사이드바 표시용)

  각 내용범주의 keywords 앞쪽에서 두 글자 이상인 것부터 고른다.
  보이는 키워드를 바꾸고 싶으면 nuri_curriculum.json의 keywords 순서를 바꾸면 된다.
  """
  limit = KEYWORDS_WHEN_CATEGORY_SELECTED if category_id else KEYWORDS_PER_CATEGORY
  groups, seen = [], set()
  for c in pool_categories(area_id, category_id):
    picked = []
    for k in c["keywords"]:
      if len(k) >= 2 and k not in seen:
        picked.append(k)
        seen.add(k)
      if len(picked) >= limit:
        break
    if picked:
      groups.append(
          {"area": c["area"], "category": c["category"], "keywords": picked}
      )
  return groups


PARTICLES = (
    "에서", "으로", "이랑", "하고",
    "이", "가", "은", "는", "을", "를", "의", "에", "도", "와", "과", "로", "랑",
)
# 조사를 떼면 한 글자 키워드로 오인되는 단어(예: 나이 → 나 + 이)
NOT_KEYWORD_WORDS = {"나이"}


def _token_forms(text: str) -> set[str]:
  """문장을 단어로 나누고, 단어 끝의 조사를 뗀 형태까지 함께 돌려준다."""
  forms: set[str] = set()
  for token in re.findall(r"[가-힣A-Za-z0-9]+", text):
    if token in NOT_KEYWORD_WORDS:
      continue
    forms.add(token)
    for p in PARTICLES:
      if token.endswith(p) and len(token) > len(p):
        forms.add(token[: -len(p)])
  return forms


def match_categories(text: str, area_id: str | None = None, top_n: int = 2):
  """자유 입력·질문 텍스트에서 키워드로 내용범주를 추정한다. (보조용)

  두 글자 이상 키워드는 문장에 포함되어 있으면 인식하고, 한 글자 키워드는
  단어(조사를 뗀 형태)와 정확히 같을 때만 인식한다.
  """
  forms = _token_forms(text)
  scored = []
  for c in pool_categories(area_id, None):
    hits = [
        k
        for k in c["keywords"]
        if (k in forms if len(k) == 1 else k in text)
    ]
    if hits:
      scored.append((len(hits), c, hits))
  scored.sort(key=lambda x: -x[0])
  return scored[:top_n]


def resolve_categories(
    area_id: str | None,
    category_id: str | None,
    keywords: list[str],
    text: str,
    fallback_text: str,
    top_n: int = 2,
) -> list[dict]:
  """이번 수업의 기준이 될 누리과정 내용범주를 정한다.

  우선순위: 고른 내용범주 > 고른 키워드 > 질문 속 키워드 > 책 소개 > 영역 전체
  """
  if category_id:
    return [get_categories_by_id()[category_id]]

  if keywords:
    scored = []
    for c in pool_categories(area_id, None):
      hits = [k for k in keywords if k in c["keywords"]]  # 정확히 일치
      if hits:
        scored.append((len(hits), c))
    scored.sort(key=lambda x: -x[0])
    if scored:
      return [c for _, c in scored[:top_n]]

  matched = match_categories(text, area_id, top_n) or match_categories(
      fallback_text, area_id, top_n
  )
  if matched:
    return [c for _, c, _ in matched]
  if area_id:
    return pool_categories(area_id, None)
  return []


MAX_TERMS = 4   # 맵에 적은 검색어 중 쓸 최대 개수 (많을수록 API 호출이 늘어난다)

def expand_keyword(keyword: str) -> list[str]:
  """선택한 주제 키워드를 실제 도서 검색에 쓸 검색어 목록으로 바꾼다.

  KEYWORD_SEARCH_MAP에 있으면 그 검색어만 쓴다(최대 MAX_TERMS개).
  맵에 없으면 키워드 그대로 + '그림책 위주' 검색을 함께 쓴다.
  """
  mapped = KEYWORD_SEARCH_MAP.get(keyword)
  if mapped:
    return mapped[:MAX_TERMS]
  if "|" in keyword:  # "a|b" 형태(여러 검색어 묶음)에는 붙이지 않는다
    return [keyword]
  return [keyword, f"{keyword} 그림책"]


def build_search_terms(
    query: str,
    area_id: str | None,
    category_id: str | None,
    keywords: list[str],
) -> list[str]:
  """제목·주제 직접 검색어 + 선택한 주제 키워드 + 누리과정 영역명을 조합하여 검색어를 만든다."""
  terms: list[str] = []
  if query.strip():
    terms.append(query.strip())  # 직접 검색어 최우선

  # 영역 이름 가져오기 (예: "신체운동·건강")
  area_name = ""
  if area_id:
    areas = get_areas()
    if area_id in areas:
      area_name = areas[area_id]["area"]

  # 키워드와 영역 이름을 조합하여 검색어 강화 (예: "신체운동 건강 가을", "가을 그림책")
  for k in keywords[:3]:
    for t in expand_keyword(k):
      terms.append(t)
      # 영역 + 키워드 조합은 '그림책' 붙은 검색어에는 만들지 않는다
      if area_name and area_name not in t and not t.endswith("그림책"):
        terms.append(f"{area_name} {t}")

  # 키워드를 안 골랐다면, 고른 영역/내용범주의 대표 키워드로 자동 검색
  if not keywords:
    if category_id:
      cats = pool_categories(area_id, category_id)
      for k in [k for c in cats for k in c["keywords"] if len(k) >= 2][:3]:
        terms.extend(expand_keyword(k))
    elif area_id:
      for c in pool_categories(area_id, None):
        first = next((k for k in c["keywords"] if len(k) >= 2), None)
        if first:
          terms.extend(expand_keyword(first))

  return list(dict.fromkeys(terms))


# =========================
# 도서관 정보나루 API
# =========================
def get_library_key() -> str | None:
  for name in LIBRARY_KEY_NAMES:
    value = os.environ.get(name)
    if value:
      return value
  return None


_call_lock = threading.Lock()
_call_count = 0
_call_date = date.today()


def _count_call(endpoint: str) -> None:
  """API 호출 수를 세고, 하루 한도에 가까워지면 ServiceError를 일으킨다.

  내 서버가 보낸 호출만 센다. 서버를 재시작하면 0으로 돌아가고, 날짜가 바뀌면 초기화된다.
  """
  global _call_count, _call_date
  with _call_lock:
    today = date.today()
    if today != _call_date:
      _call_date, _call_count = today, 0
    if _call_count >= DAILY_LIMIT:
      raise ServiceError(
          "오늘 도서 검색 호출 한도에 가까워졌어요. 내일 다시 시도해 주세요."
      )
    _call_count += 1

def _call_data4library(endpoint: str, params: dict) -> dict:
  """도서관 정보나루 API 공통 호출. 실패하면 ServiceError를 일으킨다."""
  _count_call(endpoint)

  key = get_library_key()
  if not key:
    raise ServiceError(
        "도서관 정보나루 API 키를 찾을 수 없습니다. .env의 변수 이름을"
        f" 확인하세요. (찾는 이름: {', '.join(LIBRARY_KEY_NAMES)})"
    )
  query = {"authKey": key, "format": "json", **params}
  try:
    res = requests.get(f"{DATA4LIBRARY_BASE}/{endpoint}", params=query, timeout=10)
    res.raise_for_status()
    data = res.json()
  except Exception as e:
    raise ServiceError(f"도서관 정보나루 호출에 실패했습니다: {e}") from e

  response = data.get("response", data)
  if isinstance(response, dict) and response.get("error"):
    raise ServiceError(f"도서관 정보나루 오류: {response['error']}")
  return response if isinstance(response, dict) else {}


# --- 그림책 판별 ---
EXCLUDE_CLASS_WORDS = (
    "총류", "만화", "전기",
    "사회과학", "자연과학", "기술과학",
    "철학", "종교", "역사",
)

EXCLUDE_TITLE_WORDS = (
    "장편소설", "연작소설", "단편소설", "소설집", "장편동화", "에세이", "시집",
    "학습만화", "만화", "CSI", "로봇왕", "경제", "심리학", "트레이더", "육아", "FBI",
    "초등학생", "초등", "학년",
    "Who?", "who?", "한국사", "대모험", "코믹",
    "혼한남매", "살인", "추리", "미스터리",
)

# 유아 그림책을 주로 내는 출판사 (결과에서 다른 출판사가 보이면 여기에 추가)
PICTURE_BOOK_PUBLISHERS = (
    "비룡소", "창비", "길벗어린이", "사계절", "보림", "웅진주니어", "시공주니어",
    "한솔수북", "국민서관", "책읽는곰", "천개의바람", "논장", "느림보", "반달",
    "고래이야기", "여원미디어", "한림", "키위북스", "그린북", "풀빛", "재능",
    "문학동네어린이", "푸른숲주니어", "웅진씽크빅", "소원나무", "아가월드",
    "보리", "현암주니어", "다림", "청어람", "베틀북", "별사탕", "이야기꽃",
)


def _is_blacklisted(doc: dict) -> bool:
  title = doc.get("bookname", "")
  class_nm = doc.get("class_nm", "")
  return any(w in title for w in EXCLUDE_TITLE_WORDS) or any(
      w in class_nm for w in EXCLUDE_CLASS_WORDS
  )


def is_picture_book(doc: dict) -> bool:
  """(느슨한 기준) 블랙리스트에 안 걸리고, 그림 작가 표기가 있으면 통과."""
  return not _is_blacklisted(doc) and "그림" in doc.get("authors", "")


def is_core_picture_book(doc: dict) -> bool:
  """(엄격한 기준) 블랙리스트에 안 걸리고, 그림책 전문 출판사면 통과."""
  publisher = doc.get("publisher", "")
  return not _is_blacklisted(doc) and any(
      p in publisher for p in PICTURE_BOOK_PUBLISHERS
  )


def _fetch_docs(term: str) -> list[dict]:
  """검색어 하나로 정보나루 srchBooks를 1번 호출한다."""
  response = _call_data4library(
      "srchBooks", {"keyword": term, "pageNo": 1, "pageSize": 50}
  )
  docs = []
  for row in response.get("docs", []):
    doc = row.get("doc", row)
    if doc.get("isbn13") and doc.get("bookname"):
      docs.append(doc)
  return docs


@lru_cache(maxsize=256)
def search_books(keyword: str, strict: bool = True) -> tuple[dict, ...]:
  """키워드로 도서를 검색한다. strict=True면 그림책이 아닌 책을 거른다.

  한 번 호출에 50권을 받아 우리 쪽에서 거른다. (호출 수는 그대로)
  strict일 때: 그림책 전문 출판사 → 그림 작가 표기가 있는 책 → (둘 다 없으면) 블랙리스트만 통과한 책
  정렬: 제목 관련도가 높은 책 먼저, 같으면 그림책 전문 출판사 책 먼저.
  """
  clean_query = keyword.strip()

  if "|" in clean_query:
    search_terms_to_try = [p.strip() for p in clean_query.split("|")]
  else:
    search_terms_to_try = [clean_query]
  search_terms_to_try = list(dict.fromkeys(t for t in search_terms_to_try if t))

  raw: dict[str, dict] = {}
  for term in search_terms_to_try:
    try:
      found = _fetch_docs(term)
      # 띄어쓰기가 있는 검색어는 0권이 나올 수 있어, 그때만 가장 긴 단어로 한 번 더 검색
      # ('그림책'은 너무 흔한 단어라 제외하고 주제 단어로 다시 찾는다)
      if not found and strict and " " in term:
        words = [w for w in term.split() if w != "그림책"]
        longest = max(words, key=len) if words else term
        found = _fetch_docs(longest)
      for doc in found:
        raw.setdefault(doc["isbn13"], doc)
    except ServiceError:
      raise  # IP 미등록·한도 초과 등은 화면에 오류로 보여 준다
    except Exception as e:
      logger.warning("검색 오류 term=%r → %s", term, e)
      continue

  docs = list(raw.values())
  core_ids: set[str] = set()
  if strict:
    core = [d for d in docs if is_core_picture_book(d)]
    core_ids = {d["isbn13"] for d in core}
    loose = [
        d for d in docs if d["isbn13"] not in core_ids and is_picture_book(d)
    ]
    # 아무것도 안 남으면 결과가 0권이 되지 않도록 블랙리스트만 적용한다
    docs = (core + loose) or [d for d in docs if not _is_blacklisted(d)]

  def relevance(d: dict) -> int:
    """제목에 검색어(또는 그 단어)가 들어 있을수록 앞으로."""
    title = d["bookname"].replace(" ", "")
    score = 0
    for t in search_terms_to_try:
      if t.replace(" ", "") in title:
        score += 2
      else:
        score += sum(1 for w in t.split() if len(w) >= 2 and w in title)
    return -score

  docs.sort(key=lambda d: (relevance(d), d["isbn13"] not in core_ids))
  return tuple(docs)


def _with_summary(book: dict) -> dict:
  try:
    desc = get_book_detail(book["isbn13"]).get("description", "") or ""
  except ServiceError:
    desc = ""
  desc = " ".join(html.unescape(desc).split())
  summary = desc[:80] + ("…" if len(desc) > 80 else "")
  return {**book, "description": desc, "summary": summary}


def add_summaries(books: list[dict]) -> list[dict]:
  """상세조회로 소개글을 붙인다. 동시에 호출해서 대기 시간을 줄인다."""
  with ThreadPoolExecutor(max_workers=5) as ex:
    return list(ex.map(_with_summary, books))


POOL_SIZE = 16     # 점수를 매길 후보 수 (많을수록 정확하지만 상세조회 API를 더 쓴다)
MIN_RESULTS = 0   # 주제와 맞는 책이 이보다 적어도 무관한 책으로 채우지 않는다. 

CHILD_HINTS = ("그림책", "유아", "어린이", "아기", "아가", "동화", "유치원")
OLDER_HINTS = ("초등", "저학년", "고학년", "청소년", "중학생", "성인", "어른을 위한")
ADULT_HINTS = ("에세이", "자기계발", "투자", "경영")


def _relevance(book: dict, topic_words: list[str]) -> tuple[int, int]:
  """(주제 일치 점수, 최종 점수)를 돌려준다."""
  title = book.get("bookname", "")
  desc = book.get("description", "")
  text = f"{title} {desc}"

  topical = sum(3 for w in topic_words if w in title) + sum(
      1 for w in topic_words if w in desc
  )
  score = topical
  if any(h in text for h in CHILD_HINTS):
    score += 1
  if any(h in text for h in OLDER_HINTS):
    score -= 2
  if any(h in text for h in ADULT_HINTS):
    score -= 4
  return topical, score


def _rank(
    books: list[dict], topic_words: list[str], title_ids: set[str], limit: int
) -> list[dict]:
  """주제와 맞는 정도로 책을 정렬하고, 맞지 않는 책은 뺀다."""
  if not topic_words:
    return books[:limit]

  scored = []
  for idx, b in enumerate(books):
    topical, score = _relevance(b, topic_words)
    if b["isbn13"] in title_ids:  # 직접 검색한 책은 항상 위로
      topical += 1
      score += 10
    scored.append((score, topical, idx, b))

  scored.sort(key=lambda s: (-s[0], s[2]))
  relevant = [s for s in scored if s[1] > 0]
  rest = [s for s in scored if s[1] == 0]
  picked = relevant[:limit]
  if len(picked) < MIN_RESULTS:
    picked += rest[: MIN_RESULTS - len(picked)]
  return [s[3] for s in picked]


def search_many(
    terms: list[str], limit: int | None = None, title_query: str = ""
) -> list[dict]:
  """검색어별 결과를 모아 주제와 맞는 정도로 골라 돌려준다."""
  if not terms:
    return []
  limit = limit or BOOK_LIMIT

  print(f"\n--- [체크 3/4] 도서 검색어 추출 목록: {terms} ---")

  # 검색어를 동시에 보낸다 (직접 검색어만 그림책 필터 없이)
  with ThreadPoolExecutor(max_workers=4) as ex:
    per_term = list(
        ex.map(lambda t: list(search_books(t, t != title_query)), terms)
    )

  title_lists = [r for t, r in zip(terms, per_term) if t == title_query]
  topic_lists = [r for t, r in zip(terms, per_term) if t != title_query]

  # 직접 검색 결과를 먼저 담고, 주제 검색 결과는 검색어마다 번갈아 담는다
  pool: dict[str, dict] = {}
  title_ids: set[str] = set()
  for results in title_lists:
    for b in results[:limit]:
      pool.setdefault(b["isbn13"], b)
      title_ids.add(b["isbn13"])

  target = len(pool) + POOL_SIZE
  for i in range(max((len(r) for r in topic_lists), default=0)):
    for results in topic_lists:
      if i < len(results):
        pool.setdefault(results[i]["isbn13"], results[i])
    if len(pool) >= target:
      break
  candidates = list(pool.values())[:target]

  print(f"--- [체크 3/4] 수집된 원본 후보 도서 총 수: {len(candidates)}권 ---")

  books = add_summaries(candidates)  # 소개글을 붙인다 (점수 계산에 쓴다)
  topic_words = list(
      dict.fromkeys(t.removesuffix(" 그림책") for t in terms if t != title_query)
  )

  final_books = _rank(books, topic_words, title_ids, limit)
  
  # 📌 [체크 3, 4번 증빙용] 최종 선별된 도서 개수 출력
  print(f"--- [체크 3/4] 필터링 후 최종 선별된 도서 수: {len(final_books)}권 ---\n")

  return final_books



@lru_cache(maxsize=256)
def get_book_detail(isbn13: str) -> dict:
  """ISBN으로 도서 상세 정보를 가져온다. (srchDtlList)"""
  response = _call_data4library(
      "srchDtlList", {"isbn13": isbn13, "loaninfoYN": "N"}
  )
  details = response.get("detail", [])
  if not details:
    return {}
  first = details[0]
  return first.get("book", first)


# =========================
# 근거 문서 수집 (NFR-01, NFR-02)
# =========================
def category_document(c: dict) -> dict:
  contents = "\n".join(
      f"- ({x['content_id']}) {x['content']}" for x in c["contents"]
  )
  return {
      "title": f"2019 개정 누리과정 · {c['area']} > {c['category']}",
      "url": get_curriculum()["meta"]["source_url"],
      "text": (
          f"영역: {c['area']}\n영역 목표: {c['area_goal']}\n"
          f"내용범주: {c['category']}\n내용:\n{contents}"
      ),
  }


def overview_document() -> dict:
  ov = get_curriculum()["curriculum_overview"]
  goals = "\n".join(f"- {g}" for g in ov["goals"])
  principles = "\n".join(f"- {p}" for p in ov["teaching_principles"])
  return {
      "title": "2019 개정 누리과정 총론 (목적·목표·교수학습 원칙)",
      "url": get_curriculum()["meta"]["source_url"],
      "text": (
          f"목적: {ov['purpose']}\n목표:\n{goals}\n"
          f"교수·학습 방법:\n{principles}"
      ),
  }


def collect_documents(
    book: dict,
    question: str,
    query: str,
    area_id: str | None,
    category_id: str | None,
    keywords: list[str],
) -> tuple[list[dict], list[dict]]:
  """도서 정보 + 이번 수업 주제의 누리과정 원문을 근거로 묶는다.

  (근거 문서 목록, 수업 기준이 된 내용범주 목록)을 돌려준다.
  """
  detail = get_book_detail(book["isbn13"])
  merged = {**book, **detail}
  description = html.unescape(merged.get("description") or "")

  title = merged.get("bookname", "제목 없음")
  book_doc = {
      "title": f"{title} 도서 정보 (도서관 정보나루)",
      "url": merged.get("bookDtlUrl") or "https://www.data4library.kr",
      "text": (
          f"제목: {title}\n"
          f"저자: {merged.get('authors', '정보 없음')}\n"
          f"출판사: {merged.get('publisher', '정보 없음')}\n"
          f"출판연도: {merged.get('publication_year', '정보 없음')}\n"
          f"분류: {merged.get('class_nm', '정보 없음')}\n"
          f"책 소개: {description or '제공된 소개 없음'}"
      ),
  }

  topic_cats = resolve_categories(
      area_id,
      category_id,
      keywords,
      text=f"{question} {query}",
      fallback_text=f"{title} {description}",
  )
  docs = [book_doc, *[category_document(c) for c in topic_cats], overview_document()]
  return docs, topic_cats


def cited_sources(answer: str, sources: list[dict]) -> list[dict]:
  """답변이 실제로 인용한 근거만 번호와 함께 돌려준다."""
  numbers = {
      int(n)
      for group in CITE_PATTERN.findall(answer)
      for n in group.split(",")
      if n.strip().isdigit()
  }
  return [
      {"number": i, "title": s["title"], "url": s["url"]}
      for i, s in enumerate(sources, start=1)
      if i in numbers
  ]


# =========================
# 프롬프트와 LLM 호출
# =========================
@lru_cache(maxsize=1)
def get_model() -> ChatOpenAI:
  key = os.environ.get("GMS_KEY")
  if not key:
    raise ServiceError("GMS_KEY가 없습니다. .env를 확인하세요.")
  return ChatOpenAI(model="gpt-5.4-nano", api_key=key, base_url=GMS_BASE_URL)


ROLE_INSTRUCTION = (
    "당신은 베테랑 유치원 현장 교사이자 교육과정 기획 전문가입니다.\n"
    "[답변 원칙]\n"
    "1. 톤앤매너: 전문적이고 체계적이며 현장감 있는 교사 어조를 사용하세요. (예: '~로 지도합니다', '~활동으로 연계합니다')\n"
    "2. 요청한 항목만 답변: 사용자가 묻지 않은 항목은 쓰지 마세요. 항목은 세 가지입니다.\n"
    " - 누리과정 연계: 연계되는 누리과정 영역·내용범주·내용(content_id)을 [문서]에서 찾아 명시하고 [근거 N]을 붙입니다.\n"
    " - 확장 놀이 활동: 교실에서 바로 실행 가능한 원내 수업 확장 활동 아이디어를 1~3개 제안합니다.\n"
    " - 교사-유아 상호작용 지침: 놀이를 몰입시키고 발문을 확장하는 교사 발문 가이드와 발문 예시를 작성합니다.\n"
    "   예를 들어 '확장 놀이 활동'을 물으면 활동만 쓰고, 누리과정 연계 설명이나 상호작용 지침을 별도 섹션으로 쓰지 않습니다. "
    "활동에 필요한 근거는 해당 활동 설명 안에 [근거 N]을 한 줄 정도로만 덧붙일 수 있습니다.\n"
    "3. 마무리: 문서 근거 기반 답변을 깔끔히 마친 뒤, 추가로 적용하고 싶은 생활주제가 있는지 자연스럽게 한 문장으로 물어보세요.\n"
    "4. 문체: 모든 문장은 예외 없이 '~입니다/~합니다' 존댓말로 끝내세요. 목록 항목, 화살표(→) 뒤 설명도 마찬가지입니다. "
    "누리과정 원문이 '~한다'로 끝나더라도 그대로 옮기지 말고 '~하는 내용입니다', '~하도록 안내합니다'처럼 존댓말로 풀어 쓰세요.\n"
    "5. 형식 및 가독성:\n"
    " - 답변 맨 위에 요청한 항목에 맞는 제목을 **굵게(Bold)** 한 줄로 쓰고, 번호(1), 2) 등)는 붙이지 마세요.\n"
    " - 각 주요 문단과 목록 사이에는 빈 줄(줄바꿈)을 충분히 넣어 시각적으로 시원하게 보이도록 하세요.\n"
    " - 교사-유아 발문 예시를 작성할 때는 절대 긴 줄글이나 서술형으로 풀어서 쓰지 말고, 수업 중 교사가 바로 읽을 수 있도록 각 발문은 따옴표(\"\")로 감싸고 짧은 목록 형태로 한 줄씩 깔끔하게 분리하여 작성합니다."
)


def build_prompt(
    book: dict,
    question: str,
    sources: list[dict],
    topic_cats: list[dict],
    age_band: str | None,
) -> str:
  context = "\n\n".join(
      f"[근거 {i}] {s['title']}\n{s['text']}"
      for i, s in enumerate(sources, start=1)
  )
  age_text = AGE_LABELS.get(age_band, "연령 지정 없음(만 3~5세 공통)")
  topic_text = (
      ", ".join(f"{c['area']} > {c['category']}" for c in topic_cats)
      if topic_cats
      else "지정 없음(도서 내용에 맞는 영역을 문서에서 찾아 연계)"
  )
  return (
      f"{ROLE_INSTRUCTION}\n\n"
      "아래 [문서]는 도서관 정보나루의 실제 도서 정보와 2019 개정 누리과정 원문이다.\n"
      "책의 제목·저자·출판사·소개와 누리과정 내용은 [문서]에 있는 내용만 사용하고, 없는 내용은 지어내지 않는다.\n"
      "문서에서 온 주장 뒤에는 반드시 [근거 N] 형태로 번호를 붙인다.\n"
      "수업 활동과 발문 예시는 교사의 제안으로 작성하되, 문서에 없는 책 내용(줄거리 세부 등)을 사실처럼 단정하지 않는다.\n"
      f"이번 수업의 누리과정 주제: {topic_text}. 이 책이 다른 주제에도 어울리더라도, 이번 답변은 위 주제에 맞춰 수업 내용을 구성한다.\n"
      f"대상 연령: {age_text}. 활동의 난이도와 발문은 이 연령에 맞춘다.\n"
      f"**[필수 지침] 사용자가 입력한 질문: '{question}'\n"
      "위 사용자의 질문 표현과 의도를 임의로 각색하거나 바꾸지 말고, 물어본 요구사항에 맞춰 교사용 답변을 작성할 것.**\n\n"
      f"[문서]\n{context}\n\n[선택 도서]\n{book.get('bookname', '')}\n\n[사용자 질문]\n{question}"
  )


def generate_answer(
    book: dict,
    question: str,
    query: str = "",
    area_id: str | None = None,
    category_id: str | None = None,
    keywords: list[str] | None = None,
    age_band: str | None = None,
    candidates: list[dict] | None = None,
) -> dict:
  """근거 수집 → 프롬프트 → LLM 답변. View에서는 이 함수 하나만 호출하면 된다."""
  keywords = keywords or []
  sources, topic_cats = collect_documents(
      book, question, query, area_id, category_id, keywords
  )
  prompt = build_prompt(book, question, sources, topic_cats, age_band)

  try:
    answer = get_model().invoke(prompt).content
  except ServiceError:
    raise
  except Exception as e:
    raise ServiceError(f"답변 생성 중 오류가 발생했습니다: {e}") from e

  if not answer:
    raise ServiceError(
        "답변을 생성하지 못했습니다. API 키 및 네트워크 연결을 확인해 주세요."
    )

  return {
      "answer": answer,
      "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
      "cited": cited_sources(answer, sources),
      "topics": [f"{c['area']} > {c['category']}" for c in topic_cats],
  }


# =========================
# 책 선택 전 주제 질문 → 그림책 추천
# =========================
def _norm(text: str) -> str:
  """공백·특수문자를 없애 제목을 비교하기 쉽게 만든다."""
  return re.sub(r"[\s\W_]+", "", text).lower()


def _find_book(title: str) -> dict | None:
  """AI가 말한 제목이 정보나루에 실제로 있는지 확인하고 가장 비슷한 책을 돌려준다."""
  target = _norm(title)
  if not target:
    return None

  # 쉼표·느낌표 같은 기호를 뺀 검색어도 함께 시도한다
  queries = list(dict.fromkeys([title, re.sub(r"[^\w\s]", " ", title).strip()]))

  best, best_score = None, 0.0
  for q in queries:
    try:
      candidates = search_books(q, False)  # 제목 검색은 필터 없이
    except ServiceError as e:
      print(f"[확인 오류] {q} → {e}")
      continue

    for b in candidates:
      name = _norm(b["bookname"])
      if target in name or (len(name) >= 2 and name in target):
        return b  # 포함 관계면 바로 채택
      score = SequenceMatcher(None, target, name).ratio()
      if score > best_score:
        best, best_score = b, score
  return best if best_score >= 0.7 else None


def _parse_json(raw: str) -> dict:
  start, end = raw.find("{"), raw.rfind("}")
  if start == -1 or end == -1:
    raise ServiceError("추천 결과를 읽지 못했어요. 다시 시도해 주세요.")
  try:
    return json.loads(raw[start : end + 1])
  except json.JSONDecodeError as e:
    raise ServiceError("추천 결과를 읽지 못했어요. 다시 시도해 주세요.") from e


def recommend_books(
    question: str,
    age_band: str | None = None,
    area_id: str | None = None,
    previous: list[dict] | None = None,
    candidates: list[dict] | None = None,
) -> dict:
  """주제 질문을 받아 AI가 그림책을 추천하고, 실제 존재하는 책만 돌려준다.

  previous: 이전 추천 대화 목록. 후속 질문의 맥락과 중복 방지에 쓴다.
  candidates: 정보나루에서 미리 검색해 둔 후보 책. 있으면 그 안에서만 고르게 한다.
  """
  age_text = AGE_LABELS.get(age_band, "만 3~5세 공통")
  cats = match_categories(question, area_id, 2)
  topic_text = (
      ", ".join(f"{c['area']} > {c['category']}" for _, c, _ in cats)
      if cats
      else "지정 없음"
  )

  history_text = ""
  if previous:
    lines = [
        f"- 교사 요청: {p['question']} / 추천한 책: "
        + ", ".join(b["bookname"] for b in p["books"])
        for p in previous[-3:]
    ]
    history_text = (
        "[이전 대화]\n" + "\n".join(lines) + "\n"
        "이번 요청이 이전 대화에 대한 후속 질문이면 그 맥락을 반영하세요.\n"
        "교사가 다시 요청하지 않는 한 이전에 추천한 책은 중복해서 추천하지 마세요.\n\n"
    )

  candidates_text = ""
  if candidates:
    lines = [
        f"- {b['bookname'].strip()} / {b.get('authors', '')} / {b.get('summary', '')}"
        for b in candidates[:15]
    ]
    candidates_text = (
        "[추천 후보 목록] 아래는 도서관 정보나루에서 실제로 검색된 그림책입니다.\n"
        "반드시 이 목록 안에서만 골라 추천하고, 제목은 목록에 적힌 그대로 쓰세요.\n"
        + "\n".join(lines)
        + "\n\n"
    )

  prompt = (
      "당신은 베테랑 유치원 교사이자 그림책 큐레이터입니다.\n"
      "교사의 요청에 맞는 **반드시 만 3~5세 유아 대상의 순수 창작 그림책 또는 유아용 그림책**만 최대 8권 추천하세요.\n"
      "⚠️ 절대 주의: 성인 장편소설, 추리소설, 에세이, 경제·심리 서적, 초등학생용 학습만화 및 시리즈 도서는 절대 추천하지 마세요.\n"
      "확실하지 않은 책은 넣지 말고, 제목은 정확한 정식 제목만 쓰세요.\n"
      f"{candidates_text}"
      f"대상 연령: {age_text}\n"
      f"관련 누리과정 주제(참고): {topic_text}\n\n"
      "반드시 아래 JSON 형식으로만 답하세요. 설명, 코드블록 표시는 쓰지 마세요.\n"
      '{"intro": "요청에 대한 한두 문장 안내",'
      ' "books": [{"title": "책 제목", "reason": "이 수업에 어울리는 이유 한 문장"}]}\n\n'
      f"{history_text}"
      f"[교사의 요청]\n{question}"
  )

  try:
    raw = get_model().invoke(prompt).content
  except ServiceError:
    raise
  except Exception as e:
    raise ServiceError(f"추천 중 오류가 발생했습니다: {e}") from e

  data = _parse_json(raw or "")
  items = [
      i for i in data.get("books", []) if isinstance(i, dict) and i.get("title")
  ][:8]

  # 정보나루에서 실제로 확인되는 책만 남긴다 (환각 방지)
  with ThreadPoolExecutor(max_workers=5) as ex:
    found = list(ex.map(lambda i: _find_book(i["title"]), items))

  verified, seen = [], set()
  for item, book in zip(items, found):
    if book and book["isbn13"] not in seen:
      seen.add(book["isbn13"])
      verified.append((book, item.get("reason", "")))
  verified = verified[:6]

  if not verified:
    raise ServiceError(
        "추천된 책을 도서관 정보나루에서 찾지 못했어요. 질문을 바꿔서 다시 시도해 주세요."
    )

  enriched = add_summaries([b for b, _ in verified])
  books = [
      {
          "isbn13": b["isbn13"],
          "bookname": b["bookname"],
          "authors": b.get("authors", ""),
          "publisher": b.get("publisher", ""),
          "bookImageURL": b.get("bookImageURL", ""),
          "summary": b["summary"],
          "description": b["description"],
          "reason": reason,
      }
      for b, (_, reason) in zip(enriched, verified)
  ]
  return {"question": question, "intro": data.get("intro", ""), "books": books}