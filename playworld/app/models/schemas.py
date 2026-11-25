from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PlanRequest(BaseModel):
    child_age: str = Field(default="만 4세", description="유아 연령 (예: 만 3세, 만 4세, 만 5세)")
    theme: str = Field(default="공룡과 자연", description="관심 주제")
    region: str = Field(default="용인", description="희망 방문 지역")
    visit_day: str = Field(default="토요일", description="방문 희망 요일 (월요일~일요일)")
    budget: int = Field(default=15000, ge=0, description="총 예산 한도 (원)")


class PlanResponse(BaseModel):
    id: int
    title: str
    child_age: str
    theme: str
    region: str
    visit_day: str
    budget: int
    total_cost: int
    plan_data: Dict[str, Any]
    created_at: str