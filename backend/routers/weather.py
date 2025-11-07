# routers/weather.py
"""
Weather Router - 팀원 구현 예정

날씨 API 기반 도구

아래는 예시 스케치입니다
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/weather", tags=["Weather"])

# TODO: 팀원 구현 예정
# - 날씨 API 호출
# - 실외 활동 적합성 판단
# - LangGraph Tool 인터페이스

@router.get("/current")
async def get_current_weather():
    """현재 날씨 조회 (TODO: 구현 예정)"""
    return {"message": "날씨 API 구현 예정"}