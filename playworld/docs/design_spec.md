# Nuri Town (누리타운) 상세 설계 문서

## 1. 프로젝트 개요 및 요구사항 정의서 (PRD)
* **서비스명:** Nuri Town (누리타운) — 2019 개정 누리과정 기반 AI 유아 놀이·탐험 설계 에이전트
* **기획 의도:** 기존 교사용 수업 설계 플랫폼 *Nuri Books*에서 확장하여, 유아(만 3~5세) 및 학부모·교사가 예산, 시간, 지역, 휴무일 등 실제 현실 제약을 반영한 맞춤형 놀이·독서·체험 일정을 설계하고 수정할 수 있는 인터랙티브 웹 서비스
* **핵심 기능 요구사항:**
  1. **조건 기반 AI 놀이·체험 코스 생성:** 유아 연령, 관심 주제(예: 공룡, 우주, 자연, 기본생활습관), 예산 한도, 희망 방문일/시간, 지역을 입력받아 최적의 도서+체험지 코스를 생성한다.
  2. **현실 제약 조건 검증 및 자동 재계획 (Re-planning):** 선택한 체험시설이 방문 요일에 휴무이거나, 도서 구매비+체험 입장료 합계가 예산을 초과할 경우 Agent가 스스로 대안 도서(도서관 대출 전환)나 대체 체험지를 찾아 재계획한다.
  3. **놀이 계획 CRUD 관리:** 생성된 놀이 계획을 SQLite DB에 저장하고, 목록 조회·상세 확인·조건 수정(재요청)·삭제할 수 있다.
  4. **ZEP 스타일 인터랙티브 탐험 맵 UI:** 누리타운 마을 지도(도서관 존, 과학·박물관 존, 놀이·창작 존) 위에서 AI가 추천한 코스와 캐릭터 가이드를 시각적으로 확인한다.

---

## 2. 외부 API 연동 Tool 정의서 (`app/tools/external_apis.py`)
Agent가 상황을 판단해 능동적으로 호출하는 3종의 외부 데이터 도구입니다.

| Tool 이름 | 연동 출처 | 입력 파라미터 | 반환 데이터 및 활용 목적 |
| :--- | :--- | :--- | :--- |
| `search_nuri_books` | 도서관 정보나루 (`srchBooks`) | `keyword` (주제어), `page_size` | 유아 추천 그림책 제목, 저자, 출판사, ISBN13, 표지 이미지 URL, 대출 건수 조회 |
| `get_book_price_info` | 카카오 Daum 책 검색 (`v3/search/book`) | `query` (도서명 또는 ISBN) | 도서 정가, 할인가(`sale_price`), 줄거리 요약 조회 (**예산 제약 계산용**) |
| `search_kids_places` | 공공데이터포털 TourAPI (`searchKeyword2`, `detailIntro2`) | `keyword` (지역+시설키워드), `content_id` | 어린이 박물관·과학관·체험관 목록, 주소, 이용시간, **휴무일(`restdateculture`)**, **이용요금(`usefee`)** 조회 |

---

## 3. LangGraph Agent 설계 문서 (`app/agents/planner_graph.py`)

### 3.1 Agent State 정의 (`PlannerState`)
* `user_request`: 사용자 입력 조건 (연령, 주제, 지역, 방문 요일, 예산 한도)
* `candidate_books`: 도서관 정보나루 + 카카오 책 검색으로 수집한 도서 후보 및 가격 리스트
* `candidate_places`: TourAPI로 수집한 체험시설 후보 및 요금·휴무일 정보 리스트
* `validation_errors`: 제약 조건 위반 내역 (예: `["월요일 휴관 시설 포함", "총 비용 35,000원으로 예산 20,000원 초과"]`)
* `retry_count`: 재계획 시도 횟수 (무한 루프 방지용 최대 2회 제한)
* `final_plan`: 최종 확정된 누리타운 놀이·독서·체험 코스 (JSON 구조화 출력)

### 3.2 그래프 노드(Node) 및 엣지(Edge) 흐름
1. **`collect_resources` (정보 수집 노드):** 사용자 주제와 지역을 바탕으로 `search_nuri_books`, `get_book_price_info`, `search_kids_places` Tool을 호출해 후보 데이터를 수집한다.
2. **`draft_plan` (초안 생성 노드):** 수집된 도서와 체험지를 조합해 누리과정 연계 놀이 활동 초안을 구성한다.
3. **`validate_constraints` (제약 조건 검증 노드):**
   * 방문 요일이 체험지 휴무일(`restdateculture`)과 겹치는지 검사
   * (도서 판매가 + 체험지 입장료) 총합이 사용자 예산을 초과하는지 검사
4. **조건부 분기 (`should_replan`):**
   * 검증 통과 시 → **`finalize_plan` (최종 출력 노드)** → `END`
   * 위반 발견 및 `retry_count < 2` 시 → **`replan_adjust` (자동 재계획 노드)**로 이동 (예: 도서 구매 대신 도서관 무료 대출로 전환하거나, 휴무가 아닌 대체 장소로 교체) 후 재검증
5. **`finalize_plan` (최종 출력 노드):** 유아 눈높이 안내 멘트와 보호자용 상세 일정·예산 내역을 정리해 반환한다.

---

## 4. 데이터베이스 및 API 엔드포인트 명세
* **DB (`SQLite` - `nuri_town.db`):** `play_plans` 테이블 (`id`, `title`, `age_group`, `theme`, `region`, `visit_day`, `budget`, `total_cost`, `plan_json`, `created_at`)
* **FastAPI 라우터 (`app/main.py`):**
  * `POST /api/plans/generate`: LangGraph Agent를 실행해 맞춤형 놀이 계획 생성 및 DB 저장
  * `GET /api/plans`: 저장된 놀이 계획 전체 목록 조회
  * `GET /api/plans/{plan_id}`: 특정 놀이 계획 상세 조회
  * `PUT /api/plans/{plan_id}`: 조건 변경 후 Agent 재계획 및 업데이트
  * `DELETE /api/plans/{plan_id}`: 놀이 계획 삭제