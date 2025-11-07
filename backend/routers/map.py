# routers/map.py  
"""
Map Router - 팀원 구현 예정

카카오맵 API 기반 도구

아래는 예시 스케치입니다
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/map", tags=["Map"])

# TODO: 팀원 구현 예정
# - 카카오맵 API 호출
# - 지도 데이터 생성
# - LangGraph Tool 인터페이스

@router.get("/search")
async def search_map():
    """지도 검색 (TODO: 구현 예정)"""
    return {"message": "지도 API 구현 예정"}