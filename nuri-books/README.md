# 📚 유아교육·그림책 도메인 RAG 파이프라인 서비스
> **SSAFY AI Core Project 2 - Edutech Service Planning & Content Development**

유아교육 현장(누리과정)과 그림책 데이터를 연계하여, 교사들이 수업 준비, 월별 놀이 계획, 그리고 맞춤형 발문(질문)을 효율적으로 구성할 수 있도록 지원하는 AI RAG(Retrieval-Augmented Generation) 서비스입니다.

---

## 🚀 1. 프로젝트 설명 및 실행 방법

### 주요 기능
- **누리과정 및 그림책 연계 검색:** 누리과정 영역별 내용범주와 도서관 정보나루 API 도서 데이터를 Chroma DB 벡터 저장소에 색인하여 유사도 기반 검색 제공.
- **LangGraph 기반 RAG 파이프라인:** `retrieve`(근거 탐색)와 `generate`(답변 생성) 노드를 유기적으로 연결하여 환각 현a상을 방지하고 정확한 인용([근거 N]) 제공.
- **교사 지원 도구:** 유아의 연령 및 발달 수준에 적합한 그림책 추천, 누리과정 연계 포인트 제시, 수업 활동 발문 제안.

### 기술 스택 (Tech Stack)
- **Backend:** Python, Django, LangGraph, LangChain
- **Vector DB:** Chroma DB
- **LLM & Embedding:** OpenAI API (`OpenAIEmbeddings`), GMS API
- **Environment:** dotenv, requests

### 설치 및 실행 방법 (Installation & Run)
1. **저장소 클론 및 가상환경 설정**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # (Windows 기준)
   pip install -r src/requirements.txt
   cd src
   python -m library.rag.indexer
   python manage.py runserver

2. **데이터 준비 및 작성 절차 요약**
### 1. 누리과정 데이터 로드 및 정제 (nuri_curriculum.json):

- 유아교육 누리과정의 영역, 내용범주, 세부 내용을 구조화하여 JSON 파일로 준비.

### 2. 청크(Chunk) 분할 전략:

- RecursiveCharacterTextSplitter를 활용하여 CHUNK_SIZE = 300, CHUNK_OVERLAP = 50으로 설정.

- 각 청크마다 영역 및 내용범주 헤더를 결합([영역 > 내용범주])하여 문맥 유지력 강화.

### 3. 고정 ID 및 멱등성 보장형 색인:

- content_id#n 형태의 고정 ID를 부여하고 upsert 방식을 적용하여, 동일 데이터를 여러 번 실행해도 중복 생성되지 않고 빠르게 처리되도록 최적화.

### 4. Chroma DB 벡터 저장소 구축:

- OpenAI Embeddings를 통해 임베딩 벡터를 생성하고, 코사인 유사도 기반의 벡터 컬렉션(cosine)으로 저장.

3. **사용된 데이터 출처 및 이용 조건**
### 1. 누리과정 데이터:

- 출처: 아이누리 사이트 (https://i-nuri.go.kr/main/intro.do)
       대한민국 교육부·보건복지부 고시 [2019 개정 누리과정]
       누리과정 놀이이해자료

- 이용 조건: 공공 오픈 교육 데이터로, 유아교육 및 에듀테크 연구·학습 목적의 비상업적 용도로 활용.

### 2. 도서 정보 데이터:

- 출처: 도서관 정보나루 (library.kr) 오픈 API 및 도서 대출·메타데이터 서비스.

- 이용 조건: 공공 데이터 포털 및 정보나루 오픈 API 이용 약관에 의거하여,
            도서 추천 및 교육 콘텐츠 개발 목적으로 연계 활용.

4. **프로젝트 구조**
-  ai_core_pjt2_cjh/
  ├── screenshots/
      ├── check1.png
      ├── check2.png
      ├── check3.png
      └── check7.png
  ├── .env example
  ├── .gitignore
  ├── RAG_파이프라인_설계문서.md
  ├── README.md
  ├── data/
  │   └── nuri_curriculum.json
  └── src/
      ├── chroma_db/
      ├── library/
      ├── library_nuri/
      ├── templates/
      ├── manage.py
      └── requirements.txt