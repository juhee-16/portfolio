"""
FastAPI Proxy 서버. 이 파일 하나가 서버 전부입니다. (Django 만 이 서버를 호출하고, GMS_KEY 는 여기서만 씁니다)

파일이 두 부분으로 나뉩니다.
  # 제공  — 그대로 사용합니다. 수정하지 않습니다.
  # TODO  — 요구사항 번호 순서대로 완성합니다.
          TODO 주석이 적힌 자리에 그 코드를 쓰고, 번호 1) 2) 3) … 은 그 안에서의 순서입니다.
          [F7xx] 는 그 코드를 작성하는 실습 단계입니다.

실행: uvicorn main:app --port 8081 --reload   (이 폴더 안에서)
문서: http://localhost:8081/docs
"""
import base64
import json
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from schemas import (
    ChatGuardrailRequest,
    ChatGuardrailResponse,
    ChatRequest,
    ChatResponse,
    ChatScoreRequest,
    ChatScoreResponse,
    DecideRouteRequest,
    DecideRouteResponse,
    GenerateSpeechRequest,
    GenerateSpeechResponse,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    ImageGenerationRequest,
    ImageGenerationResponse,
)

load_dotenv(".env")
GMS_KEY = os.getenv("GMS_KEY")
GMS_URL = os.getenv("GMS_URL")
HEADERS = {"Authorization": f"Bearer {GMS_KEY}"}

MODEL_NANO = "gpt-5-nano"       # 가볍고 저렴한 모델
MODEL_MINI = "gpt-5-mini"       # 더 성능 좋은 모델
MODEL_IMAGE = "gpt-image-2"  # GMS 에는 dall-e 가 없음. 응답은 URL 이 아니라 b64_json
# TODO [F711] (심화)
#   1) 아래 줄의 주석을 풀어 MODEL_TTS 상수를 정의한다.
MODEL_TTS = "gpt-4o-mini-tts"

app = FastAPI(title="Book Recommend Proxy (FastAPI)")


# ######################################################################
# 제공 — 그대로 사용합니다. 수정하지 않습니다.
# ######################################################################

def ask_gms(messages, model=MODEL_NANO, response_format=None):
    """채팅 모델에 messages 를 보내고, 답변 문자열만 돌려줍니다."""
    payload = {"model": model, "messages": messages}
    if response_format:
        payload["response_format"] = response_format
    # gms_post 는 아래 F706 에 있음 (파이썬은 호출 시점에 함수를 찾으므로 순서는 상관없다)
    response = gms_post("/chat/completions", payload)
    return response.json()["choices"][0]["message"]["content"]


# ######################################################################
# TODO — 요구사항 번호 순서대로 완성합니다.
# ######################################################################

# ---------------------------------------------------------------- F702 텍스트 추천 생성 (+F703, F710)
@app.post("/api/v1/chat/completions", response_model=ChatResponse)
def chat_completions(request: ChatRequest):
    # TODO [F703]  — 생성보다 먼저 실행되어야 하므로 이 자리에 쓴다
    user_text = request.messages[-1]["content"]
    ensure_appropriate(user_text)

    # TODO [F710] (심화)
    model = MODEL_NANO
    if request.use_tier_routing and decide_model_tier(user_text) == "complex":
        model = MODEL_MINI
    
    # TODO [F702]
    content = ask_gms(request.messages, model)
    return {"content": content, "model_used": model}


# ---------------------------------------------------------------- F703 Guardrail
GUARDRAIL_PROMPT = """
너는 도서 추천 서비스의 입력 검사기이다. 사용자의 요청이 적절한지 판단한다. 

[부적절 (is_appropriate = false)] 아래처럼 명백한 경우만 해당한다. 
- 폭력, 자해, 혐오 표현, 성인 콘텐츠를 요구하는 경우
- 명백히 불법인 행위의 방법을 묻는 경우 (예: 마약 제조법, 해킹 방법)
- 다른 사람의 개인정보를 요구하는 경우

[적절 (is_appropriate = true)]
- 위에 해당하지 않는 모든 요청.
- 판단이 모호하면 적절한 것으로 본다. 
- 폭력이나 범죄를 다룬 책을 추천해 달라는 일반적인 도서 요청은 적절하다. 

is_appropriate 값만 JSON으로 답한다. 
"""


@app.post("/api/v1/chat/guardrail", response_model=ChatGuardrailResponse)
def chat_guardrail(request: ChatGuardrailRequest):
    # TODO [F703]
    #   1) messages = [developer(GUARDRAIL_PROMPT), user(request.prompt)] 를 만든다.
    #   2) response_format 을 만든다. → 명세서 F703 의 response_format 예시를 그대로 사용한다.
    #   3) answer = ask_gms(messages, MODEL_NANO, response_format) 을 호출하고
    #      result = json.loads(answer) 로 JSON 을 해석한다.
    #   4) {"is_appropriate": result["is_appropriate"]} 를 반환한다.
    messages = [
        {"role": "developer", "content": GUARDRAIL_PROMPT},
        {"role": "user", "content": request.prompt},
    ]
    
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "guardrail_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"is_appropriate": {"type": "boolean"}},
                "required": ["is_appropriate"],
                "additionalProperties": False
            },
        },
    }
    
    answer = ask_gms(messages, MODEL_NANO, response_format)
    result = json.loads(answer)
    return {"is_appropriate": result["is_appropriate"]}


def ensure_appropriate(prompt):
    """생성 함수들이 맨 먼저 호출합니다. 부적절하면 403 오류를 냅니다."""
    # TODO [F703]
    #   1) result = chat_guardrail(ChatGuardrailRequest(prompt=prompt)) 를 호출한다.
    #   2) result["is_appropriate"] 가 False 이면
    #      HTTPException(status_code=403, detail="inappropriate request") 을 발생시킨다.
    result = chat_guardrail(ChatGuardrailRequest(prompt=prompt))
    if not result["is_appropriate"]:
        raise HTTPException(status_code=403, detail="inappropriate request")


# ---------------------------------------------------------------- F704 라우트 결정
ROUTE_PROMPT = """
너는 도서 추천 서비스의 요청 분류기이다. 사용자의 요청을 읽고 어떤 기능으로 처리할지 고른다.
- 책 추천, 책에 대한 질문, 독서 상담처럼 글로 답해야 하는 요청이면 "/chat/completions"
- 책 표지를 그려 달라, 표지 이미지를 만들어 달라는 등 이미지를 만들어야 하는 요청이면 "/images/generations"
판단이 애매하면 "/chat/completions" 를 고른다.
"""


@app.post("/api/v1/decide-route", response_model=DecideRouteResponse)
def decide_route(request: DecideRouteRequest):
    # TODO [F704]
    #   1) messages = [developer(ROUTE_PROMPT), user(request.prompt)] 를 만든다.
    #   2) response_format 은 F703 것을 복사해 properties 를
    #      route(string, enum: ["/chat/completions", "/images/generations"]) 로 바꾼다.
    #   3) ask_gms 의 답변을 json.loads 로 해석해 {"route": ...} 를 반환한다.
    messages = [
        {'role':'developer', 'content':ROUTE_PROMPT},
        {'role':'user', 'content': request.prompt},
    ]
    response_format = {
        'type':'json_schema',
        'json_schema':{
            'name':'route_response',
            'strict':True,
            'schema':{
                'type':'object',
                'properties':{
                    'route':{
                        'type':'string',
                        'enum':["/chat/completions", "/images/generations"],
                    }
                },
                'required':['route'],
                'additionalProperties':False,
            },
        },
    }
    answer = ask_gms(messages, MODEL_NANO, response_format)
    result = json.loads(answer)
    return {'route':result['route']}

# ---------------------------------------------------------------- F705 이미지 생성 (+F703)
@app.post("/api/v1/images/generations", response_model=ImageGenerationResponse)
def image_generations(request: ImageGenerationRequest):
    # TODO [F703]
    #   1) ensure_appropriate(request.prompt) 를 호출한다.
    ensure_appropriate(request.prompt)
    # TODO [F705]
    #   1) payload = {"model": MODEL_IMAGE, "prompt": request.prompt, "size": "1024x1024",
    #                 "quality": "low", "output_format": "jpeg"}   (quality·output_format 은 토큰·파일 크기 절약)
    #   2) response = gms_post("/images/generations", payload) 를 호출하고
    #      image_base64 = response.json()["data"][0]["b64_json"] 을 꺼낸다. (이미지가 base64 문자열로 바로 온다)
    #   3) {"image_base64": image_base64} 를 반환한다.
    payload = {
        'model':MODEL_IMAGE,
        'prompt':request.prompt,
        'size':'1024x1024',
        'quality':'low',
        'output_format':'jpeg',
    }
    response = gms_post('/images/generations', payload)
    image_base64 = response.json()['data'][0]['b64_json']
    return {'image_base64':image_base64}

# ---------------------------------------------------------------- F706 공통 에러 처리
def gms_post(path, payload):
    """GMS 에 POST 요청을 보냅니다. 모든 GMS 호출이 이 함수를 거칩니다."""
    response = requests.post(GMS_URL + path, headers=HEADERS, json=payload, timeout=120)
    # TODO [F706]
    if response.status_code != 200:
        print("[GMS 호출 실패]", path, response.status_code, response.text[:200])
        raise HTTPException(status_code=503, detail="model server error")
    return response


# ---------------------------------------------------------------- F707 이미지 분석 (+F703)
ANALYSIS_PROMPT = """
너는 책 표지 분석 도우미이다. 사용자가 올린 책 표지 사진을 보고 다음 순서로 한국어로 답한다. 
1. 표지에서 읽을 수 있는 제목과 저자(보이는 경우)를 알려준다. 
2. 표지의 그림, 색감, 분위기를 바탕으로 장르를 추정한다. 
3. 비슷한 분위기의 도서를 2~3권 추천하고, 각각 한두문장으로 이유를 설명한다. 
표지에서 제목을 알아볼 수 없으면 추정이라고 밝히고, 사용자의 질문에도 함께 답한다. 
"""


@app.post("/api/v1/images/analysis", response_model=ImageAnalysisResponse)
def image_analysis(request: ImageAnalysisRequest):
    # TODO [F703]
    ensure_appropriate(request.question)
    

    # TODO [F707]
    image_url = "data:image/png;base64," + request.image_base64
    user_content = [
        {"type": "image_url", "image_url": {"url": image_url}},
        {"type": "text", "text": request.question},
    ]
    messages = [
        {"role": "developer", "content": ANALYSIS_PROMPT},
        {"role": "user", "content": user_content},
    ]
    content = ask_gms(messages, MODEL_NANO)
    return {"content": content}


# ---------------------------------------------------------------- F709 텍스트 응답 점수 계산 (심화)
SCORE_PROMPT = """
너는 도서 추천 답변의 평가자이다. 앞선 대화에서 사용자의 요청과, 마지막에 주어진 '답변'을 보고 
그 답변이 사용자의 취향과 상황에 얼마나 적합한지 평가한다. 
- score: 0~100 사이의 정수. (요청과 잘 맞고 구체적일수록 높게)
- reason: 점수를 준 이유를 한두문장의 한국어로 쓴다. 
"""

@app.post("/api/v1/chat/score", response_model=ChatScoreResponse)
def chat_score(request: ChatScoreRequest):
    ensure_appropriate(request.messages[-1]["content"])
    # TODO [F709]
    messages = (
        [{"role": "developer", "content": SCORE_PROMPT}]
        + request.messages
        + [{"role": "user", "content": "답변: " + request.answer}]
    )
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "score_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["score", "reason"],
                "additionalProperties": False,
            },
        },
    }
    
    answer = ask_gms(messages, MODEL_NANO, response_format)
    result = json.loads(answer)
    return {"score": result["score"], "reason": result["reason"]}

# ---------------------------------------------------------------- F710 모델 등급 라우팅 (심화)
TIER_PROMPT = """
너는 도서 추천 요청의 난이도를 분류하는 분류기이다. 
- "simple": 장르나 주제 같은 조건이 하나뿐인 간단한 요청. (예: "소설 추천해줘")
- "complex": 조건이 여러 개이거나, 감정·상황·분위기를 종합해서 판단해야 하는 요청.
    (예: "비 오는 날 혼자 읽기 좋은, 위로가 되는 짧은 에세이")
tier 값만 JSON으로 답한다. 
"""


def decide_model_tier(prompt):
    # TODO [F710]
    messages = [
        {"role": "developer", "content": TIER_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "tier_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"tier": {"type": "string", "enum": ["simple", "complex"]}},
                "required": ["tier"],
                "additionalProperties": False,
            },
        },
    }
    answer = ask_gms(messages, MODEL_NANO, response_format)
    result = json.loads(answer)
    return result["tier"]
# ---------------------------------------------------------------- F711 TTS (심화)
@app.post("/api/v1/generate-speech", response_model=GenerateSpeechResponse)
def generate_speech(request: GenerateSpeechRequest):
    # TODO [F711]  — 파일 위쪽의 MODEL_TTS 상수도 함께 정의한다
    #   1) payload = {"model": MODEL_TTS, "input": request.text, "voice": "nova", "response_format": "mp3"}
    #   2) response = gms_post("/audio/speech", payload) 를 호출한다.
    #   3) audio_data = base64.b64encode(response.content).decode("utf-8") 로 인코딩한다.
    #   4) {"audio_data": audio_data} 를 반환한다.
    payload = {
        'model':MODEL_TTS,
        'input':request.text,
        'voice':'nova',
        'response_format':'mp3',
    }
    response = gms_post('/audio/speech', payload)
    audio_data = base64.b64encode(response.content).decode('utf-8')
    return {'audio_data':audio_data}