# 부산 여행 대시보드

부산 관광 정보를 한 곳에서 확인하고, 여행 게시판과 챗봇을 함께 사용할 수 있는 Vue 3 기반 대시보드입니다.

## 구현된 기능

- 부산 관광지/숙박/문화시설/쇼핑 정보를 메인 화면에서 확인
- 카테고리 필터와 검색을 통한 장소 탐색
- 게시판 CRUD(목록, 상세, 작성, 수정, 삭제)
  - 작성 시 입력한 비밀번호로만 수정/삭제 가능 (SHA-256 해시로 저장)
  - 게시글 조회수 증가 (같은 브라우저 세션에서 같은 글은 1회만 카운트)
- 좋아요 / 북마크
- 댓글 기능 (LocalStorage + BroadcastChannel 기반 브라우저 간 동기화)
- 챗봇 위젯: 장소 후보는 로컬 키워드 매칭으로 고르고, 답변 문장은 Netlify Function을 통해 OpenAI(GPT)가 자연스러운 구어체로 생성 (함수 미배포/키 미설정 시 고정 템플릿으로 자동 폴백)

## 기술 스택

- Vite + Vue 3
- Vue Router
- ES Modules 기반 구조
- LocalStorage / SessionStorage 기반 데이터 저장 (별도 백엔드 없음)

## 폴더 구조

```text
src/
  components/
    board/      # 게시판 UI 컴포넌트 (PasswordModal, DeleteConfirmModal 등)
    chat/       # 챗봇 UI
    common/     # 공통 헤더/푸터
    map/        # 지도/장소 리스트 UI
  views/        # 페이지 단위 뷰
  services/     # 외부 API/서비스 로직 (recommendService, storageService, commentsService)
  utils/        # 게시글 저장소(storage.js) 및 유틸 함수
  router/       # 라우터 설정
public/
  data/         # 부산 공공데이터 JSON 및 설명 문서
scripts/        # 데이터 정규화용 스크립트
netlify/
  functions/    # 서버리스 함수 (chat.js: OpenAI 호출용, API 키는 여기서만 사용)
```

## 실행 방법

```bash
npm install
npm run dev
```

개발 서버가 실행되면 브라우저에서 앱을 확인할 수 있습니다. 단, 이 명령은 순수 Vite 서버라 `/.netlify/functions/*` 경로가 없어서 챗봇은 자동으로 로컬 템플릿 응답으로 폴백합니다.

챗봇의 실제 GPT 응답까지 로컬에서 테스트하려면:

```bash
npm run dev:functions
```

`netlify dev`를 실행해 Vite 서버와 서버리스 함수를 함께 띄웁니다. 프로젝트 루트에 `OPENAI_API_KEY`가 설정된 `.env` 계열 파일이 있어야 합니다(`.env.local`은 git에 커밋되지 않습니다).

기본 모델은 `gpt-5-mini`입니다. OpenAI 프로젝트마다 접근 가능한 모델이 다르므로(예: `model_not_found` 403 에러) 다른 모델을 쓰려면 `OPENAI_MODEL` 환경 변수를 추가하세요. `gpt-5-mini`/`o1-mini` 같은 reasoning 계열 모델은 `temperature` 커스텀 값을 지원하지 않고 `max_tokens` 대신 `max_completion_tokens`를 쓰므로, `gpt-4o`/`gpt-3.5-turbo` 같은 일반 채팅 모델로 바꾸는 경우 `netlify/functions/chat.js`의 요청 파라미터도 함께 되돌려야 합니다.

## 사용 가능한 스크립트

| 명령                  | 설명                                          |
| --------------------- | --------------------------------------------- |
| `npm run dev`         | 개발 서버 실행 (챗봇은 템플릿 응답으로 동작)  |
| `npm run dev:functions` | Netlify Function 포함 로컬 실행 (GPT 응답 테스트) |
| `npm run build`       | 프로덕션 빌드                                |
| `npm run preview`     | 빌드 결과 미리보기                            |
| `npm run build:data`  | 공공데이터 정규화 스크립트 실행               |
| `npm run lint`        | ESLint 검사 및 자동 수정                      |
| `npm run format`      | Prettier 포맷 실행                            |

## 현재 데이터 저장 방식

- 게시글/댓글/좋아요/북마크는 브라우저의 LocalStorage에 저장됩니다.
- 게시글 비밀번호는 평문이 아니라 SHA-256 해시로 저장되지만, 검증 로직 자체가 클라이언트(JS)에서 돌기 때문에 개발자 도구로 우회 가능한 **데모용 보호 장치**입니다. 실 서비스 전환 시 서버 사이드 인증으로 반드시 교체해야 합니다.
- 조회수 중복 증가 방지는 SessionStorage 기준이라 시크릿 창이나 다른 브라우저에서는 다시 카운트됩니다.
- 지도 데이터는 [public/data](public/data) 아래의 JSON 파일을 불러옵니다.
- 챗봇 장소 후보는 `src/services/recommendService.js`의 키워드 매칭으로 고르고, 답변 문장은 `netlify/functions/chat.js`(서버리스 함수)가 `OPENAI_API_KEY`로 OpenAI를 호출해 생성합니다. API 키는 서버리스 함수 안에서만 쓰이므로 브라우저 번들에는 노출되지 않습니다. 함수 호출이 실패하거나(키 미설정, 네트워크 오류 등) 함수 자체가 없는 환경(`npm run dev`)이면 기존 고정 템플릿 응답으로 자동 폴백합니다.

## 테스트용 게시글 비밀번호

- 최초 실행 시 시드로 들어가는 게시글 7개(`post-001` ~ `post-007`)의 비밀번호는 모두 `1234`입니다.
- 직접 작성한 게시글은 작성 시 입력한 비밀번호로 수정/삭제하세요.

## 데이터 출처

부산 공공데이터는 한국관광공사 TourAPI 4.0 기반으로 정리되어 있으며, 자세한 내용은 [public/data/SOURCE.md](public/data/SOURCE.md)와 [public/data/SCHEMA.md](public/data/SCHEMA.md)를 참고하세요.

## 참고 사항

- 현재 프로젝트는 로컬 데모/프로토타입 형태로 구성되어 있으며, 실제 서비스 수준의 백엔드 연동(인증, DB, 실시간 댓글 서버 등)은 별도로 보강해야 합니다.
- Netlify에 배포할 때는 사이트 환경 변수(Site settings → Environment variables)에 `OPENAI_API_KEY`를 등록해야 챗봇이 실제 GPT 응답을 생성합니다. `VITE_` 접두사를 붙이면 브라우저에 노출되니 절대 사용하지 마세요.
