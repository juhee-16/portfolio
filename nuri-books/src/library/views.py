from django.shortcuts import redirect, render

from . import services
from .rag.service import ask_rag

HISTORY_LIMIT = 20
DISCOVER_LIMIT = 8  # 추천 대화는 최근 8턴까지 보관

# 월별/생활 주제 키워드 목록 정의
# 여기 적힌 이름이 사이드바에 보이고, 그대로 도서 검색어로도 쓰인다.
# (services.KEYWORD_SEARCH_MAP이 비어 있는 동안은 보이는 것 = 검색되는 것)
MONTHLY_KEYWORDS = [
    "친구", "봄", "여름", "가을", "겨울",
    "동물", "곤충", "가족", "우리동네", "직업",
    "교통기관", "우리나라", "세계여러나라", "환경",
    "색과모양", "학교",
]


def index(request):
  """검색 폼(GET) + 질문 처리(POST)를 한 페이지에서 처리한다."""
  context = {
      "disclaimer": services.DISCLAIMER,
      "presets": [(k, v[0]) for k, v in services.PRESET_PROMPTS.items()],
      "ages": list(services.AGE_LABELS.items()),
      "error": None,
  }

  try:
    areas = services.get_areas()
    categories_by_id = services.get_categories_by_id()
  except services.ServiceError as e:
    context["error"] = str(e)
    return render(request, "library/index.html", context)

  # --- 1. 필터 값 읽기---
  area_id = request.GET.get("area") or None
  if area_id not in areas:
    area_id = None

  category_id = request.GET.get("category") or None
  if category_id:
    category = categories_by_id.get(category_id)
    if not area_id or not category or category["area_id"] != area_id:
      category_id = None

  # 월별 놀이 주제 키워드 (여러 개 선택 가능)
  shown_keywords = set(MONTHLY_KEYWORDS)
  keywords = [k for k in request.GET.getlist("keywords") if k in shown_keywords]

  query = request.GET.get("q", "").strip()
  age_band = request.GET.get("age") or None
  if age_band not in services.AGE_LABELS:
    age_band = None

  # --- 2. 도서 검색 ---
  terms = services.build_search_terms(query, area_id, category_id, keywords)
  books = []
  if terms:
    try:
      books = services.search_many(terms, title_query=query)
    except services.ServiceError as e:
      context["error"] = str(e)

  # 선택 전 주제 질문 대화 (이전에 추천된 책도 고를 수 있게 함께 찾아 둔다)
  discover_history = request.session.get("discover_history", [])
  books_by_isbn = {b["isbn13"]: b for b in books}
  for d in discover_history:
    for b in d["books"]:
      books_by_isbn.setdefault(b["isbn13"], b)

  isbn = request.GET.get("isbn") or None
  book = books_by_isbn.get(isbn)

  # --- 3. 질문 처리 ---
  history = request.session.get("history", [])
  qs = request.GET.urlencode()
  here = f"{request.path}?{qs}" if qs else request.path

  if request.method == "POST":
    if "clear" in request.POST:
      request.session["history"] = []
      return redirect(here)

    # 3-1. 대화 지우기
    if "discover_clear" in request.POST:
      request.session["discover_history"] = []
      return redirect(here)

    # 3-2. 책 선택 전 주제 질문 → 그림책 추천
    if "discover_q" in request.POST:
      discover_q = request.POST.get("discover_q", "").strip()
      if discover_q:
        try:
          result = services.recommend_books(
              discover_q,
              age_band=age_band,
              area_id=area_id,
              previous=discover_history,
          )
        except services.ServiceError as e:
          context["error"] = str(e)
        else:
          discover_history.append(result)
          request.session["discover_history"] = discover_history[-DISCOVER_LIMIT:]
          return redirect(f"{here}#discover-last") 

    # 3-3. 선택한 책에 대한 수업 설계 질문
    preset = request.POST.get("preset")
    if preset in services.PRESET_PROMPTS:
      question = services.PRESET_PROMPTS[preset][1]
    else:
      question = request.POST.get("question", "").strip()

    if book and question:
      try:
        extra = " ".join(keywords)
        desc = (book.get("summary") or "")[:80]
        result = ask_rag(f"{book['bookname']} {extra} {desc} 그림책과 연계해서: {question}")
      except services.ServiceError as e:
        context["error"] = str(e)
      else:
        history.append({"isbn": isbn, "question": question, **result})
        request.session["history"] = history[-HISTORY_LIMIT:]
        return redirect(here)

  # --- 4. 화면에 넘길 값 ---
  context.update(
      {
          "areas": list(areas.values()),
          "area_id": area_id,
          "categories": areas[area_id]["categories"] if area_id else [],
          "category_id": category_id,
          "monthly_keywords": MONTHLY_KEYWORDS, 
          "keywords": keywords,
          "query": query,
          "age_band": age_band,
          "terms": terms,
          "books": books,
          "isbn": isbn,
          "book": book,
          "qs": qs,
          "discover_history": discover_history,
          "history": [h for h in history if h.get("isbn") == isbn] if book else [],
      }
  )
  return render(request, "library/index.html", context)