# routers/map.py
"""
Map Router - KakaoMap API 연동 예정
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/map",
    tags=["Map"]
)

@router.get(
    "/search",
    summary="지도 검색",
    description="KakaoMap API 호출하여 마커 데이터 반환 (구현 예정)"
)
async def search_map():
    """지도 검색 도구 (팀원 구현 예정)"""
    return {"message": "지도 API 구현 예정"}


