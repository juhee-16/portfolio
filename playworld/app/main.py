import asyncio
import uuid
from app.events import bus, event_logs, logging_agent
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from typing import List
from app.models.schemas import PlanRequest, PlanResponse
from app.database import (
    init_db, create_plan, get_all_plans, get_plan_by_id, update_plan, delete_plan,
    get_all_students, create_student, update_student, delete_student, add_student_stamp,
    save_artwork, get_all_artworks, save_guestbook, get_all_guestbooks
)
from app.agents.planner_graph import run_nuri_planner

app = FastAPI(title="Nuri Town (누리타운) AI 놀이 설계 서비스", version="1.0.0")


@app.on_event("startup")
def on_startup():
    init_db()


# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== 4개 역할별 HTML 페이지 분리 라우팅 ====================
@app.get("/")
def page_login():
    return FileResponse("static/login.html")


@app.get("/index")
def page_teacher_index():
    return FileResponse("static/index.html")


@app.get("/detail")
def page_student_detail():
    return FileResponse("static/detail.html")


@app.get("/play")
def page_kid_play():
    return FileResponse("static/play.html")


@app.get("/kid")
def page_kid_login():
    return FileResponse("static/kid_login.html")

@app.post("/api/plans/generate", response_model=PlanResponse)
def generate_play_plan(req: PlanRequest):
    try:
        req_dict = req.model_dump()
        final_plan = run_nuri_planner(req_dict)
        total_cost = final_plan["cost_summary"]["total_cost"]
        title = final_plan.get("plan_title", f"[{req.region}] {req.theme} 탐험 코스")

        saved = create_plan(
            title=title,
            child_age=req.child_age,
            theme=req.theme,
            region=req.region,
            visit_day=req.visit_day,
            budget=req.budget,
            total_cost=total_cost,
            plan_data=final_plan,
        )
        return saved
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="놀이 계획 생성 중 오류가 발생했습니다. 입력값과 서버 설정을 확인해 주세요.",
        ) from exc


@app.get("/api/plans", response_model=List[PlanResponse])
def list_play_plans():
    return get_all_plans()


@app.get("/api/plans/{plan_id}", response_model=PlanResponse)
def retrieve_play_plan(plan_id: int):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="해당 놀이 계획을 찾을 수 없습니다.")
    return plan


@app.put("/api/plans/{plan_id}", response_model=PlanResponse)
def regenerate_play_plan(plan_id: int, req: PlanRequest):
    existing = get_plan_by_id(plan_id)
    if not existing:
        raise HTTPException(status_code=404, detail="수정할 놀이 계획을 찾을 수 없습니다.")

    req_dict = req.model_dump()
    final_plan = run_nuri_planner(req_dict)
    total_cost = final_plan["cost_summary"]["total_cost"]
    title = final_plan.get("plan_title", f"[{req.region}] {req.theme} 탐험 코스")

    updated = update_plan(
        plan_id=plan_id,
        title=title,
        child_age=req.child_age,
        theme=req.theme,
        region=req.region,
        visit_day=req.visit_day,
        budget=req.budget,
        total_cost=total_cost,
        plan_data=final_plan,
    )
    return updated


@app.delete("/api/plans/{plan_id}")
def remove_play_plan(plan_id: int):
    if not delete_plan(plan_id):
        raise HTTPException(status_code=404, detail="삭제할 놀이 계획을 찾을 수 없습니다.")
    return {"message": "놀이 계획이 삭제되었습니다.", "id": plan_id}

@app.get("/api/students")
def api_list_students():
    return get_all_students()


@app.post("/api/students")
def api_create_student(data: dict = Body(...)):
    return create_student(
        name=data.get("name", "새 친구"),
        age=data.get("age", "만 4세"),
        avatar=data.get("avatar", "🐶"),
        memo=data.get("memo", "")
    )


@app.put("/api/students/{student_id}")
def api_update_student(student_id: int, data: dict = Body(...)):
    return update_student(
        student_id=student_id,
        name=data.get("name", "친구"),
        age=data.get("age", "만 4세"),
        avatar=data.get("avatar", "🐶"),
        memo=data.get("memo", "")
    )


@app.post("/api/students/{student_id}/stamp")
def api_add_stamp(student_id: int):
    return add_student_stamp(student_id)


@app.delete("/api/students/{student_id}")
def api_delete_student(student_id: int):
    delete_student(student_id)
    return {"status": "deleted"}

@app.get("/api/artworks")
def api_list_artworks():
    return get_all_artworks()

@app.post("/api/artworks")
def api_create_artwork(data: dict = Body(...)):
    sid = uuid.uuid4().hex[:8]
    bus.publish(
        "artwork.uploaded",
        sid,
        student_name=data.get("student_name", "꼬마 화가"),
        avatar=data.get("avatar", "🐶"),
        theme=data.get("theme", "누리타운 탐험"),
    )
    return save_artwork(
        student_name=data.get("student_name", "꼬마 화가"),
        avatar=data.get("avatar", "🐶"),
        theme=data.get("theme", "누리타운 탐험"),
        image_data=data.get("image_data", "")
    )

@app.get("/api/guestbooks")
def api_list_guestbooks():
    return get_all_guestbooks()

@app.post("/api/guestbooks")
def api_create_guestbook(data: dict = Body(...)):
    raw_msg = data.get("message", "").strip()
    emoji = data.get("emoji", "😄")
    name = data.get("student_name", "꼬마 탐험가")
    # 아이가 말로 남긴 짧은 문장을 예쁜 방문록 기록으로 다듬기
    formatted = f"{name} 탐험가의 이야기: \"{raw_msg}\"" if raw_msg else f"{name} 탐험가가 {emoji} 기분으로 신나게 놀고 갔어요!"
    return save_guestbook(
        student_name=name,
        avatar=data.get("avatar", "🐶"),
        emoji=emoji,
        message=formatted
    )

@app.get("/api/events/stream")
async def stream_events():
    queue = bus.register_stream()

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            bus.unregister_stream(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/events/logs")
def get_event_logs():
    return event_logs[-30:]

@app.get("/api/logs/sessions")
def list_log_sessions():
    return logging_agent.list_sessions()


@app.get("/api/logs/sessions/{session_id}")
def get_log_session_detail(session_id: str):
    items = logging_agent.get_session_detail(session_id)
    if not items:
        raise HTTPException(status_code=404, detail="해당 세션의 실행 로그를 찾을 수 없습니다.")
    return {"session_id": session_id, "logs": items}


@app.delete("/api/logs/sessions/{session_id}")
def delete_log_session(session_id: str):
    deleted = logging_agent.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="삭제할 세션 로그를 찾을 수 없습니다.")
    return {"deleted": True, "session_id": session_id}