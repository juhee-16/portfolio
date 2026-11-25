import asyncio
import json
from collections import defaultdict
from datetime import datetime


class EventBus:
    def __init__(self):
        self._subs = []
        self._sse_queues = []

    def subscribe(self, fn):
        self._subs.append(fn)

    def publish(self, event, session_id, **payload):
        msg = {
            "event": event,
            "session_id": session_id,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }
        for fn in list(self._subs):
            try:
                fn(msg)
            except Exception:
                pass  # 로깅/구독자 오류가 발생해도 메인 실행은 중단하지 않음

        raw = json.dumps(msg, ensure_ascii=False)
        for q in list(self._sse_queues):
            try:
                q.put_nowait(raw)
            except Exception:
                pass
        return msg

    def register_stream(self):
        q = asyncio.Queue()
        self._sse_queues.append(q)
        return q

    def unregister_stream(self, q):
        if q in self._sse_queues:
            self._sse_queues.remove(q)


class SessionLoggingAgent:
    """LLM을 사용하지 않고 발행된 이벤트를 세션별로 순서대로 수집·저장하는 로깅 에이전트."""

    def __init__(self):
        self._sessions = defaultdict(list)

    def handle_event(self, msg: dict):
        sid = msg.get("session_id") or "default"
        self._sessions[sid].append({
            "event": msg.get("event"),
            "ts": msg.get("ts"),
            "payload": msg.get("payload", {}),
        })

    def list_sessions(self):
        result = []
        for sid, items in self._sessions.items():
            result.append({
                "session_id": sid,
                "event_count": len(items),
                "started_at": items[0]["ts"] if items else None,
                "ended_at": items[-1]["ts"] if items else None,
            })
        return result

    def get_session_detail(self, session_id: str):
        return list(self._sessions.get(session_id, []))

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


bus = EventBus()
event_logs = []
logging_agent = SessionLoggingAgent()

bus.subscribe(event_logs.append)
bus.subscribe(logging_agent.handle_event)
bus.subscribe(lambda m: print(f"📢 [{m['ts']}] {m['event']} ({m['session_id']}): {m['payload']}"))