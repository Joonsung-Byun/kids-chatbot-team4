# routers/weather.py
"""
Weather Router - 날씨 API 연동 예정
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/weather",
    tags=["Weather"]
)

@router.get(
    "/current",
    summary="현재 날씨 조회",
    description="외부 날씨 API 호출 (구현 예정)"
)
async def get_current_weather():
    """현재 날씨 도구 (팀원 구현 예정)"""
    return {"message": "날씨 API 구현 예정"}