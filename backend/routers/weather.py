# routers/weather.py
"""
Weather Router - 기상청 API 연동
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from services.weather_service import get_weather
from utils.logger import logger

router = APIRouter(
    prefix="/weather",
    tags=["Weather"]
)


@router.get(
    "/current",
    summary="현재 날씨 조회",
    description="기상청 API 또는 캐시된 데이터로 현재 날씨를 조회합니다."
)
async def get_current_weather(
    location: str = Query(..., description="지역명 (예: 서울, 강남)"),
    date: Optional[str] = Query(None, description="날짜 (예: 오늘, 내일, YYYY-MM-DD)")
):
    """
    현재 날씨 API
    """
    try:
        logger.info(f"🌦️ 날씨 조회 요청: {location}, date={date}")
        result = get_weather(location=location, target_date=date)
        return {
            "success": True,
            "location": location,
            "date": date or "오늘",
            "data": result
        }
    except Exception as e:
        logger.error(f"❌ 날씨 API 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="날씨 정보를 가져오는 중 오류가 발생했습니다.")