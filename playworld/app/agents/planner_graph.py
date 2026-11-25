import json
import uuid
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.events import bus
from app.tools.external_apis import search_nuri_books, get_book_price_info, search_kids_places


class PlannerState(TypedDict):
    user_request: Dict[str, Any]
    candidate_books: List[Dict[str, Any]]
    candidate_places: List[Dict[str, Any]]
    selected_book: Dict[str, Any]
    selected_place: Dict[str, Any]
    book_acquire_mode: str          # "purchase" (구매) 또는 "library_loan" (도서관 무료 대출)
    validation_errors: List[str]
    agent_logs: List[str]           # Agent의 사고·검증·재계획 로그 (UI 시각화용)
    retry_count: int
    final_plan: Dict[str, Any]


def _get_llm():
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.4,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    return ChatOpenAI(**kwargs)


def _score_place_for_theme(place: Dict[str, Any], theme: str) -> int:
    text = f"{place.get('name', '')} {place.get('address', '')} {place.get('fee_text', '')}".lower()
    t = (theme or "").lower()
    score = 0

    theme_keywords = {
        "우주": ["우주", "별", "천문", "과학", "박물관", "체험", "관찰"],
        "별": ["별", "우주", "천문", "과학", "박물관", "자연"],
        "바다": ["바다", "해양", "수족관", "물", "생태", "아쿠아", "과학"],
        "공룡": ["공룡", "자연", "박물관", "생태", "화석", "과학"],
    }

    for key, kws in theme_keywords.items():
        if key in t:
            for kw in kws:
                if kw in text:
                    score += 3

    for word in t.replace("반짝이는", "").replace("탐험", "").split():
        if len(word) >= 2 and word in text:
            score += 2

    return score


def _score_book_for_toddler(book: Dict[str, Any], theme: str) -> int:
    title = (book.get("title") or "").lower()
    contents = (book.get("contents") or "").lower()
    text = f"{title} {contents}"
    score = 0

    for kw in ["그림책", "유아", "동화", "놀이"]:
        if kw in text:
            score += 2

    for word in (theme or "").lower().replace("반짝이는", "").replace("탐험", "").split():
        if len(word) >= 2 and word in text:
            score += 2

    for bad_kw in ["장편동화", "과학 상식", "상식", "쿠키런", "학습", "만화", "문제집", "전집"]:
        if bad_kw in text:
            score -= 5

    return score


# Node 1: 외부 API 3종을 호출해 후보 데이터 수집
def collect_resources(state: PlannerState) -> Dict[str, Any]:
    req = state["user_request"]
    theme = req.get("theme", "놀이")
    region = req.get("region", "용인")
    logs = list(state.get("agent_logs", []))

    logs.append(f"🔍 [정보 수집] '{theme}' 주제의 유아 그림책과 '{region}' 지역 체험 공간을 조회합니다.")
    raw_books = search_nuri_books(keyword=theme, page_size=3)
    enriched_books = []
    for b in raw_books:
        price_info = get_book_price_info(b["title"])
        b["price"] = price_info["price"]
        b["contents"] = price_info["contents"]
        if not b["image_url"]:
            b["image_url"] = price_info["thumbnail"]
        enriched_books.append(b)

    if enriched_books:
        enriched_books = sorted(
            enriched_books,
            key=lambda b: _score_book_for_toddler(b, theme),
            reverse=True,
        )

    places = search_kids_places(region=region, theme=theme, num_of_rows=4)
    if places:
        places = sorted(
            places,
            key=lambda p: _score_place_for_theme(p, theme),
            reverse=True,
        )

    if not enriched_books:
        enriched_books = [{
            "title": f"{theme} 탐험 그림책",
            "authors": "누리작가",
            "publisher": "누리출판",
            "price": 12000,
            "image_url": "",
            "contents": f"{theme}에 대해 재미있게 배우는 유아 그림책입니다.",
        }]
    if not places:
        places = [{
            "name": f"{region} 어린이 상상놀이터",
            "address": f"{region}시 누리길 10",
            "rest_date": "연중무휴",
            "use_time": "10:00~18:00",
            "fee_text": "무료",
            "fee_amount": 0,
        }]

    logs.append(f"📚 도서 후보 {len(enriched_books)}권, 🏛️ 체험 공간 후보 {len(places)}곳 수집 완료.")
    return {
        "candidate_books": enriched_books,
        "candidate_places": places,
        "selected_book": enriched_books[0],
        "selected_place": places[0],
        "book_acquire_mode": "purchase",
        "retry_count": 0,
        "agent_logs": logs,
    }


# Node 2: 현실 제약 조건 검증 (휴무일 + 예산 초과)
def validate_constraints(state: PlannerState) -> Dict[str, Any]:
    req = state["user_request"]
    visit_day = req.get("visit_day", "수요일")
    budget = int(req.get("budget", 15000))
    book = state["selected_book"]
    place = state["selected_place"]
    mode = state["book_acquire_mode"]
    logs = list(state["agent_logs"])

    errors = []

    rest_date = place.get("rest_date", "")
    if visit_day and visit_day in rest_date:
        errors.append(f"휴무일 충돌: '{place['name']}'은(는) {visit_day}에 휴관합니다 ({rest_date}).")

    book_cost = 0 if mode == "library_loan" else int(book.get("price", 0))
    place_cost = int(place.get("fee_amount", 0))
    total_cost = book_cost + place_cost

    if total_cost > budget:
        errors.append(
            f"예산 초과: 총 예상 비용 {total_cost:,}원(도서 {book_cost:,}원 + 입장료 {place_cost:,}원)이 설정 예산 {budget:,}원을 초과했습니다."
        )

    if errors:
        for err in errors:
            logs.append(f"⚠️ [제약 검증 실패] {err}")
    else:
        logs.append(f"✅ [제약 검증 통과] {visit_day} 방문 가능 및 총 비용 {total_cost:,}원 (예산 {budget:,}원 이내).")

    return {
        "validation_errors": errors,
        "agent_logs": logs,
    }


# Node 3: 제약 위반 시 자동 재계획 (Re-planning)
def replan_adjust(state: PlannerState) -> Dict[str, Any]:
    req = state["user_request"]
    visit_day = req.get("visit_day", "수요일")
    budget = int(req.get("budget", 15000))
    errors = state["validation_errors"]
    logs = list(state["agent_logs"])
    retry = state["retry_count"] + 1

    book = state["selected_book"]
    place = state["selected_place"]
    mode = state["book_acquire_mode"]

    logs.append(f"🔄 [자동 재계획 #{retry}] 현실 제약을 해결하기 위해 코스를 재조정합니다...")

    if any("휴무일 충돌" in e for e in errors):
        alt_places = [p for p in state["candidate_places"] if visit_day not in p.get("rest_date", "")]
        if alt_places:
            place = alt_places[0]
            logs.append(f"   ↳ 대체 공간 선택: '{place['name']}' (휴무일: {place['rest_date']})")
        else:
            place = {
                "name": f"{req.get('region', '우리동네')} 공공 어린이도서관 & 집콕 놀이방",
                "address": f"{req.get('region', '우리동네')} 시립어린이도서관",
                "rest_date": "연중무휴 (가정 연계 활동 포함)",
                "use_time": "09:00~18:00",
                "fee_text": "무료",
                "fee_amount": 0,
            }
            logs.append(f"   ↳ 지역 박물관 전체 휴관일로 인해 '{place['name']}'(무료)로 코스를 전환했습니다.")

    if any("예산 초과" in e for e in errors):
        if mode == "purchase":
            mode = "library_loan"
            logs.append(f"   ↳ 비용 절감 전략: '{book['title']}' 구매({book.get('price', 0):,}원) 대신 도서관 무료 대출(0원)로 전환!")
        if int(place.get("fee_amount", 0)) > budget:
            free_places = [p for p in state["candidate_places"] if int(p.get("fee_amount", 0)) <= budget and visit_day not in p.get("rest_date", "")]
            if free_places:
                place = free_places[0]
            else:
                place = {
                    "name": f"{req.get('region', '우리동네')} 어린이 생태공원 & 도서관",
                    "address": f"{req.get('region', '우리동네')} 중앙공원 내",
                    "rest_date": "연중무휴",
                    "use_time": "상시 개방",
                    "fee_text": "무료",
                    "fee_amount": 0,
                }
            logs.append(f"   ↳ 입장료 예산 초과로 무료 체험 공간 '{place['name']}'으로 변경!")

    return {
        "selected_book": book,
        "selected_place": place,
        "book_acquire_mode": mode,
        "retry_count": retry,
        "agent_logs": logs,
    }


def should_replan(state: PlannerState) -> str:
    if state["validation_errors"] and state["retry_count"] < 2:
        return "replan"
    return "finalize"


# Node 4: 최종 놀이·탐험 코스 + AI 다이내믹 월드 테마 생성 (2019 개정 누리과정 연계)
def finalize_plan(state: PlannerState) -> Dict[str, Any]:
    req = state["user_request"]
    theme = req.get("theme", "공룡과 자연")
    book = state["selected_book"]
    place = state["selected_place"]
    mode = state["book_acquire_mode"]
    logs = list(state["agent_logs"])

    book_cost = 0 if mode == "library_loan" else int(book.get("price", 0))
    place_cost = int(place.get("fee_amount", 0))
    total_cost = book_cost + place_cost

    enriched_candidates = []
    for cb in state.get("candidate_books", [book]):
        cb_copy = dict(cb)
        cb_copy["applied_cost"] = 0 if mode == "library_loan" else int(cb.get("price", 0))
        enriched_candidates.append(cb_copy)

    default_world_theme = {
        "sky_top": "#7dd3fc",
        "sky_bottom": "#bae6fd",
        "ground_top": "#86efac",
        "ground_bottom": "#4ade80",
        "floating_emojis": ["☁️", "🦋", "🌿"],
        "memory_pairs": [
            {"icon": "🦕", "label": "브라키오"},
            {"icon": "🦖", "label": "티라노"},
            {"icon": "🥚", "label": "공룡알"},
            {"icon": "🌿", "label": "나뭇잎"},
            {"icon": "📖", "label": "그림책"},
        ],
        "treasures": [
            {"icon": "💎", "name": "반짝이는 파란 보석"},
            {"icon": "👑", "name": "황금 왕관 보물"},
            {"icon": "🗝️", "name": "비밀 보물 열쇠"},
            {"icon": "🪙", "name": "반짝반짝 금화"},
            {"icon": "🎁", "name": "알록달록 선물상자"},
        ],
        "stickers": ["🦕", "⭐", "❤️", "🌈"],
    }

    guide_data = {
        "plan_title": f"[{req.get('region')}] {theme} 누리타운 탐험 코스",
        "nuri_domain": "자연탐구 · 의사소통 · 예술경험 영역 (2019 개정 누리과정)",
        "kid_greeting": f"안녕 꼬마 탐험가! 오늘은 '{book['title']}' 이야기를 읽고 '{place['name']}'으로 신나는 모험을 떠나볼까?",
        "world_theme": default_world_theme,
        "activities": [
            {
                "zone": "📚 1코스: 누리 북카페 존 (사전 독서 놀이)",
                "title": f"그림책 '{book['title']}' 함께 읽고 상상 질문하기",
                "description": f"책 속 주인공이 만나는 {theme} 친구들의 표정과 움직임을 몸으로 흉내 내며 호기심을 키워요.",
            },
            {
                "zone": "🏛️ 2코스: 누리 탐험 광장 존 (현장 체험 놀이)",
                "title": f"'{place['name']}'에서 보물찾기 미션 수행",
                "description": f"책에서 본 장면을 실제 공간({place['address']})에서 찾아보고, 가장 마음에 드는 1가지를 사진이나 그림으로 기록해요.",
            },
            {
                "zone": "🎨 3코스: 누리 창작 공방 존 (사후 확장 놀이)",
                "title": "나만의 작은 탐험 일기 & 만들기 놀이",
                "description": "집에 돌아와 오늘 본 장면을 재활용 종이나 클레이로 만들어 보며 부모님·친구에게 이야기해 주어요.",
            },
        ],
    }

    if settings.OPENAI_API_KEY:
        try:
            llm = _get_llm()
            prompt = f"""
당신은 2019 개정 누리과정에 정통한 유아 에듀테크 놀이 및 게임 월드 디자이너입니다.
아래 확정된 주제와 도서·체험 장소 정보를 바탕으로 유아({req.get('child_age')})를 위한 놀이 코스 및 주제 맞춤형 월드 테마 JSON을 작성하세요.

- 놀이 주제: {theme}
- 확정 도서: {book['title']} (이용 방식: {'도서관 무료 대출' if mode == 'library_loan' else '도서 구매'})
- 확정 체험지: {place['name']} ({place['address']})
- 총 비용: {total_cost}원 (예산: {req.get('budget')}원)

[중요 규칙]
world_theme 안의 색상과 모든 이모지·단어는 반드시 '{theme}'의 세부 맥락에 100% 어울리도록 새로 창작하세요.
예) '우주'면 어두운 밤하늘 색(#0f172a, #1e1b4b)과 로켓·행성 이모지, '봄에 오는 황사'면 옅은 모래하늘(#fef3c7)과 마스크·손씻기·봄꽃 이모지.

반드시 아래 JSON 키 구조를 정확히 지키세요 (코드블록 없이 순수 JSON만 출력):
{{
  "plan_title": "코스 제목",
  "nuri_domain": "관련 누리과정 영역 (예: 자연탐구 · 의사소통 영역)",
  "kid_greeting": "유아에게 다정하게 건네는 2문장 이내의 탐험 초대 멘트",
  "world_theme": {{
    "sky_top": "#HEX색상코드 (하늘 위쪽 배경색)",
    "sky_bottom": "#HEX색상코드 (하늘 아래쪽 배경색)",
    "ground_top": "#HEX색상코드 (땅 위쪽 배경색)",
    "ground_bottom": "#HEX색상코드 (땅 아래쪽 배경색)",
    "floating_emojis": ["하늘에 떠다니는 주제 관련 이모지 3개"],
    "memory_pairs": [
      {{"icon": "주제 관련 이모지1", "label": "4글자이내단어1"}},
      {{"icon": "주제 관련 이모지2", "label": "4글자이내단어2"}},
      {{"icon": "주제 관련 이모지3", "label": "4글자이내단어3"}},
      {{"icon": "주제 관련 이모지4", "label": "4글자이내단어4"}},
      {{"icon": "주제 관련 이모지5", "label": "4글자이내단어5"}}
    ],
    "treasures": [
      {{"icon": "보물이모지1", "name": "형용사 포함 보물 이름1"}},
      {{"icon": "보물이모지2", "name": "형용사 포함 보물 이름2"}},
      {{"icon": "보물이모지3", "name": "형용사 포함 보물 이름3"}},
      {{"icon": "보물이모지4", "name": "형용사 포함 보물 이름4"}},
      {{"icon": "보물이모지5", "name": "형용사 포함 보물 이름5"}}
    ],
    "stickers": ["그림판용 주제 스티커 이모지 4개"]
  }},
  "activities": [
    {{"zone": "📚 1코스: 누리 북카페 존", "title": "활동명", "description": "구체적인 유아 놀이 방법 2문장"}},
    {{"zone": "🏛️ 2코스: 누리 탐험 광장 존", "title": "활동명", "description": "구체적인 현장 놀이 방법 2문장"}},
    {{"zone": "🎨 3코스: 누리 창작 공방 존", "title": "활동명", "description": "가정 연계 사후 미술/신체 놀이 2문장"}}
  ]
}}
"""
            res = llm.invoke([SystemMessage(content="순수 JSON만 출력하는 유아 에듀테크 월드 디자이너 AI입니다."), HumanMessage(content=prompt)])
            raw_text = res.content.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw_text)
            if "activities" in parsed:
                guide_data.update(parsed)
            logs.append(f"✨ [최종 완성] '{theme}' 주제 맞춤형 AI 다이내믹 월드 테마 및 놀이 가이드를 생성했습니다.")
        except Exception as e:
            logs.append(f"ℹ️ 기본 누리과정 템플릿으로 코스를 구성했습니다. ({str(e)[:40]})")

    final_plan = {
        **guide_data,
        "candidate_books": enriched_candidates,
        "selected_book": {
            **book,
            "acquire_mode": "도서관 무료 대출 (0원)" if mode == "library_loan" else f"도서 구매 ({book_cost:,}원)",
            "applied_cost": book_cost,
        },
        "selected_place": {
            **place,
            "applied_cost": place_cost,
        },
        "book": {
            **book,
            "acquire_mode": "도서관 무료 대출 (0원)" if mode == "library_loan" else f"도서 구매 ({book_cost:,}원)",
            "applied_cost": book_cost,
        },
        "place": {
            **place,
            "applied_cost": place_cost,
        },
        "cost_summary": {
            "budget": int(req.get("budget", 15000)),
            "book_cost": book_cost,
            "place_cost": place_cost,
            "total_cost": total_cost,
            "remaining_budget": int(req.get("budget", 15000)) - total_cost,
        },
        "agent_logs": logs,
    }

    return {"final_plan": final_plan}


def build_planner_graph():
    workflow = StateGraph(PlannerState)
    workflow.add_node("collect_resources", collect_resources)
    workflow.add_node("validate_constraints", validate_constraints)
    workflow.add_node("replan_adjust", replan_adjust)
    workflow.add_node("finalize_plan", finalize_plan)

    workflow.set_entry_point("collect_resources")
    workflow.add_edge("collect_resources", "validate_constraints")
    workflow.add_conditional_edges(
        "validate_constraints",
        should_replan,
        {
            "replan": "replan_adjust",
            "finalize": "finalize_plan",
        },
    )
    workflow.add_edge("replan_adjust", "validate_constraints")
    workflow.add_edge("finalize_plan", END)

    return workflow.compile()


planner_agent = build_planner_graph()


def run_nuri_planner(request_data: Dict[str, Any]) -> Dict[str, Any]:
    sid = uuid.uuid4().hex[:8]
    emit = lambda event, **p: bus.publish(event, sid, **p)

    emit("planner.start", theme=request_data.get("theme"), region=request_data.get("region"))
    initial_state: PlannerState = {
        "user_request": request_data,
        "candidate_books": [],
        "candidate_places": [],
        "selected_book": {},
        "selected_place": {},
        "book_acquire_mode": "purchase",
        "validation_errors": [],
        "agent_logs": [],
        "retry_count": 0,
        "final_plan": {},
    }
    result = planner_agent.invoke(initial_state)
    final_plan = result["final_plan"]
    emit(
        "planner.end",
        title=final_plan.get("plan_title", ""),
        book=final_plan.get("selected_book", {}).get("title", ""),
        place=final_plan.get("selected_place", {}).get("name", ""),
    )
    return final_plan